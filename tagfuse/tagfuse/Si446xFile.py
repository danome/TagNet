# coding: utf-8

# Si446x Device Direct Access Byte File (Dblk and Panic)

from __future__ import print_function
from builtins import *                  # python3 types
from time import sleep
from datetime import datetime
import struct as pystruct
from binascii import hexlify
import os.path
import sys
from collections import defaultdict, OrderedDict
from time import time

sys.path.append("../si446x/si446x")
from Si446xDevice import *

sys.path.append("../tagnet/tagnet")
from tagnet import TagMessage, TagGet, TagPut, TagHead
from tagnet import TagName
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet.tagtlv import TlvListBadException, TlvBadException

# default paramters
MAX_WAIT            = 10
MAX_RECV            = 255
MAX_PAYLOAD         = 254
MAX_RETRIES         = 10
RADIO_POWER         = 100
SHORT_DELAY         = 0

def show_radio_config(radio, config):
    si446x_device_show_config(radio.dump_radio())
    total = 0
    print('\n=== const config strings:')
    for s in config:
        print((hexlify(s)))
        total += len(s) - 4
    print('\n total: {}'.format(total))
    # ## Get Chip Status
    print(radio.get_chip_status())

def si446x_device_enable():
    # ##  Start up Radio
    radio = si446x_device_start_radio()
#    si446x_device_show_config(radio.dump_radio())
    # ## Check for Command Error
    status = radio.get_chip_status()
    if (status.chip_pend.CMD_ERROR):
        print(status)
    # ##  Configure Radio
    config = si446x_device_config_radio(radio)
#    show_radio_config(radio, config)
    return radio


def file_payload2dict(payload, keynames):
    '''
    extract variable number of parameters in payload and then
    filter for the parameters of interest.
    '''
    plist = []
    for tv in payload:
        plist.append((tv.tlv_type(), tv.value()))
    dfile = OrderedDict(plist)
#    print(dfile)
    plist = []
    for item in keynames:
        try:
            plist.append(dfile[item])
        except:
            plist.append(None)
    return plist

def file_get_bytes(radio, devname, fileno, amount_to_get, file_offset):
    '''
    File Byte Data Transfer function
    '''
    accum_bytes = bytearray()
    eof = False

    def _file_bytes_msg(devname, fileno, amount_to_get, file_offset):
        # / <node_id> / "tag" / "sd" / 0 / devname [/ fileno]
        tlv_list = [TagTlv(tlv_types.NODE_ID, -1),
                    TagTlv('tag'),
                    TagTlv('sd'),
                    TagTlv(0),
                    TagTlv(devname),
                    TagTlv('byte')]
        if (fileno): tlv_list.append(TagTlv(fileno))
        tlv_list.extend([TagTlv(tlv_types.OFFSET, file_offset),
                         TagTlv(tlv_types.SIZE, amount_to_get)])
        tname = TagName(tlv_list)
        print(tname)
        return TagGet(tname).build()

    while (amount_to_get):
        req_msg = _file_bytes_msg(devname, fileno, amount_to_get, file_offset)
        # zzz print(hexlify(req_msg)
        si446x_device_send_msg(radio, req_msg, RADIO_POWER);
        rsp_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, 5)
        if(rsp_msg):
            # zzz print(len(rsp_msg), hexlify(rsp_msg))
            try:
                rsp = TagMessage(rsp_msg)
            except (TlvListBadException, TlvBadException):
                print(len(rsp_msg), hexlify(rsp_msg))
                props = radio.get_property('PKT', 0x0b, 2)
                print('fifo threshold (rx/tx): {}/{}'.format(props[1],
                                                             props[0]))
                props = radio.fifo_info()
                print('fifo depth:             {}/{}'.format(props[0],
                                                             props[1]))
                break
            # zzz print("{}".format(rsp.header.options.param.error_code))
            # zzz print(rsp.payload)
            file_rsp_pl_types = [tlv_types.OFFSET,
                                 tlv_types.SIZE,
                                 tlv_types.BLOCK,
                                 tlv_types.EOF,
                                 tlv_types.ERROR]
            offset, amt2get, block, eof, err = file_payload2dict(rsp.payload,
                                                                 file_rsp_pl_types)
            # zzz
            print('read pos:{}, len:{}'.format(offset, amt2get))
            if (block):
                accum_bytes   += block
                file_offset   += len(block)
                amount_to_get -= len(block)
            if (err):
                if (err == tlv_errors.EBUSY):
                    # zzz print('busy')
                    continue
                elif (err == tlv_errors.EODATA):
                    print('end of file, offset: {}'.format(offset))
                    eof = True
                    break
                else:
                    print('unexpected error: {}, offset: {}'.format(err, offset))
                    break
            if (eof):
                print('eof: {}'.format(offset))
                break
            else:
                eof = False
            if (offset) and (offset != file_offset):
                print('bad offset, expected: {}, got: {}'.format(
                    file_offset, offset))
                break
            if (amt2get) and (amt2get != amount_to_get):
                print('bad size, expected: {}, got: {}'.format(
                    amount_to_get, amt2get))
                break
        else:
            print('TIMEOUT')
            break
    # zzz print('read p/l:{}/{}'.format(file_offset-len(accum_bytes), len(accum_bytes)))
    return accum_bytes, eof

def dblk_get_bytes(radio, amount_to_get, file_offset):
    return file_get_bytes(radio, 'dblk', 0, amount_to_get, file_offset)

def panic_get_bytes(radio, fileno, amount_to_get, file_offset):
    return file_get_bytes(radio, 'panic', fileno, amount_to_get, file_offset)

def file_update_attrs(radio, devname, fileno, attrs):
    '''
    Adds devname and filename to end of TagNet path to create reference to a file fact,
    either:
     / <node_id> / "tag" / "sd" / 0 / str(devname) / int(filename)
    or:
     / <node_id> / "tag" / "sd" / 0 / str(devname) / str(filename)
    where:
     devname = "dblk" | "panic"
     filename = "byte" | "note"
    '''
    def get_file_tlv(filename):
        try:
            return TagTlv(tlv_types.INTEGER, int(filename))
        except ValueError:
            pass
        try:
            return TagTlv(tlv_types.STRING, bytearray(filename,'utf-8'))
        except ValueError:
            print('file name not valid: {}'.format(fn))
            return None

    def _file_attr_msg(ftlv):
        file_name = TagName([TagTlv(tlv_types.NODE_ID, -1),
                             TagTlv('tag'),
                             TagTlv('sd'),
                             TagTlv(0),
                             TagTlv(devname),
                             ftlv,])
        return TagHead(file_name).build()

    ftlv = get_file_tlv(filename)
    # zzz print(ftlv)
    if (ftlv == None):
        print('file_attr bad name tlv')
        return attrs
    req_msg = _file_attr_msg(ftlv)
    if (req_msg == None):
        print('file_attr bad request msg')
        return attrs

    # zzz print(hexlify(req_msg))
    si446x_device_send_msg(radio, req_msg, RADIO_POWER);
    rsp_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, 5)
    if(rsp_msg):
        # zzz print(hexlify(rsp_msg))
        rsp = TagMessage(rsp_msg)
        # zzz print("{}".format(rsp.header.options.param.error_code))
        # zzz print(rsp.payload)
        file_rsp_pl_types = [tlv_types.SIZE,
                             # zzz tlv_types.UTC_TIME,
                             tlv_types.ERROR,
        ]
        filesize, err = file_payload2dict(rsp.payload,
                                          file_rsp_pl_types)
        if err and err is not tlv_errors.SUCCESS:
            print('file_attr error in response: {}'.format(err))
            filesize = 0
        attrs['st_size']  = filesize
        attrs['st_mtime'] = time()
    return attrs

def dblk_write_note(radio, note):
    dblk_rsp_pl_types = [tlv_types.SIZE,
                         tlv_types.ERROR,
    ]

    def _dblk_note_msg(note):
        # / <node_id> / "tag" / "sd" / 0 / "dblk" / "note"
        dblk_name = TagName([TagTlv(tlv_types.NODE_ID, -1),
                     TagTlv('tag'),
                     TagTlv('sd'),
                     TagTlv(0),
                     TagTlv('dblk'),
                     TagTlv('note'),])
        msg = TagPut(dblk_name, pl=bytearray(note))
        return msg.build()

    req_msg = _dblk_note_msg(note)
    # zzz print(hexlify(req_msg))
    si446x_device_send_msg(radio, req_msg, RADIO_POWER);
    rsp_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, 5)
    if(rsp_msg):
        # zzz print(hexlify(rsp_msg))
        rsp = TagMessage(rsp_msg)
        # zzz print("{}".format(rsp.header.options.param.error_code))
        # zzz print(rsp.payload)
        amt, error = dblk_payload2dict(rsp.payload,
                                       dblk_rsp_pl_types)
        # zzz print(amt, error)
        if (error == tlv_errors.SUCCESS):
            return amt
    return 0

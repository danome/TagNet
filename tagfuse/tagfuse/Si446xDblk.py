# coding: utf-8

# # Si446x Device Direct Access Tag Position Tracker

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
sys.path.append("../tagnet/tagnet")
from tagnet import TagMessage, TagGet, TagPut, TagHead
from tagnet import TagName
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors

from Si446xDevice import *

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


def dblk_payload2dict(payload, keynames):
    '''
    extract variable number of parameters in payload and then
    filter for the parameters of interest.
    '''
    plist = []
    for tv in payload:
        plist.append((tv.tlv_type(), tv.value()))
    ddblk = OrderedDict(plist)
#    print(ddblk)
    plist = []
    for item in keynames:
        try:
            plist.append(ddblk[item])
        except:
            plist.append(None)
    return plist


def dblk_get_bytes(radio, fileno, amount_to_get, file_offset):
    '''
    Dblk Byte Data Transfer function
    '''
    accum_bytes = bytearray()
    eof = False
    dblk_rsp_pl_types = [tlv_types.OFFSET,
                         tlv_types.SIZE,
                         tlv_types.BLOCK,
                         tlv_types.EOF,
                         tlv_types.ERROR]

    def _dblk_bytes_msg(fileno, amount_to_get, file_offset):
        # / <node_id> / "tag" / "sd" / 0 / "dblk" / fileno
        dblk_name = TagName([TagTlv(tlv_types.NODE_ID, -1),
                     TagTlv('tag'),
                     TagTlv('sd'),
                     TagTlv(0),
                     TagTlv('dblk'),
                     TagTlv(fileno),
                     TagTlv(tlv_types.OFFSET, file_offset),
                     TagTlv(tlv_types.SIZE, amount_to_get),])
        return TagGet(dblk_name).build()

    while (amount_to_get):
        req_msg = _dblk_bytes_msg(fileno, amount_to_get, file_offset)
        # zzz
        print(hexlify(req_msg))
        si446x_device_send_msg(radio, req_msg, RADIO_POWER);
        rsp_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, 5)
        if(rsp_msg):
            # zzz
            print(hexlify(rsp_msg))
            rsp = TagMessage(rsp_msg)
            # zzz print("{}".format(rsp.header.options.param.error_code))
            # zzz print(rsp.payload)
            offset, amt2get, block, eof, err = dblk_payload2dict(rsp.payload,
                                                                 dblk_rsp_pl_types)
            # zzz print('read pos:{}, len:{}'.format(offset, amt2get))
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

def dblk_update_attrs(radio, fileno, attrs):
    dblk_rsp_pl_types = [tlv_types.SIZE,
                         # zzz tlv_types.UTC_TIME,
                         tlv_types.ERROR,
    ]

    def _dblk_attr_msg():
        # / <node_id> / "tag" / "sd" / 0 / "dblk" / fileno
        dblk_name = TagName([TagTlv(tlv_types.NODE_ID, -1),
                             TagTlv('tag'),
                             TagTlv('sd'),
                             TagTlv(0),
                             TagTlv('dblk'),
                             TagTlv(fileno),])
        return TagHead(dblk_name).build()

    req_msg = _dblk_attr_msg()
    print(hexlify(req_msg))
    si446x_device_send_msg(radio, req_msg, RADIO_POWER);
    rsp_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, 5)
    if(rsp_msg):
        # zzz
        print(hexlify(rsp_msg))
        rsp = TagMessage(rsp_msg)
        # zzz print("{}".format(rsp.header.options.param.error_code))
        # zzz
        # zzz
        print(rsp.payload)
        filesize, file_time = dblk_payload2dict(rsp.payload,
                                                dblk_rsp_pl_types)
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
        # zzz
        print(rsp.payload)
        amt, error = dblk_payload2dict(rsp.payload,
                                       dblk_rsp_pl_types)
        if (error == tlv_errors.SUCCESS):
            return amt
    return 0

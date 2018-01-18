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

__all__ = ['file_get_bytes',
           'file_put_bytes',
           'file_update_attrs',
           'dblk_put_note']

from Si446xDevice import *
from Si446xUtils import file_payload2dict, path2tlvs

sys.path.append("../tagnet")
from tagnet import TagMessage, TagGet, TagPut, TagHead
from tagnet import TagName
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet.tagtlv import TlvListBadException, TlvBadException

# default paramters
MAX_WAIT            = .3
MAX_RECV            = 255
MAX_PAYLOAD         = 254
MAX_RETRIES         = 10
RADIO_POWER         = 100
SHORT_DELAY         = 0

def file_get_bytes(radio, devname, fileno, amount_to_get, file_offset):
    '''
    File Byte Data Transfer function
    '''
    global RADIO_POWER, MAXR_RETRIES
    accum_bytes = bytearray()
    eof = False

    def _file_bytes_msg(devname, fileno, amount_to_get, file_offset):
        # / <node_id> / "tag" / "sd" / 0 / devname / byte [/ fileno]
        tlv_list = [TagTlv(tlv_types.NODE_ID, -1),
                    TagTlv('tag'),
                    TagTlv('sd'),
                    TagTlv(0),
                    TagTlv(devname.encode('ascii','ignore')),
                    TagTlv('byte')]
        if (int(fileno)): tlv_list.append(TagTlv(tlv_types.INTEGER, int(fileno)))
        tlv_list.extend([TagTlv(tlv_types.OFFSET, file_offset),
                         TagTlv(tlv_types.SIZE, amount_to_get)])
        tname = TagName(tlv_list)
        # zzz print(tname)
        return TagGet(tname).build()

    while (amount_to_get):
        req_msg = _file_bytes_msg(devname, fileno, amount_to_get, file_offset)
        # zzz print(hexlify(req_msg))
        si446x_device_send_msg(radio, req_msg, RADIO_POWER)
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
            # zzz print('read pos: {}, len: {}, error: {}'.format(offset, amt2get, err))
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

def file_update_attrs(radio, path_list, attrs):
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

    def _file_attr_msg(path_list):
        tname = TagName(path2tlvs(path_list))
        # zzz
        print('file update attrs', path_list, tname)
        return TagHead(tname).build()

    req_msg = _file_attr_msg(path_list)
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
        # zzz
        print(rsp.payload)
        filesize, err = file_payload2dict(rsp.payload,
                                          [tlv_types.SIZE,
                                           # zzz tlv_types.UTC_TIME,
                                           tlv_types.ERROR,])
        if err and err is not tlv_errors.SUCCESS:
            print('file_attr error in response: {}'.format(err))
            filesize = 0
        attrs['st_size']  = filesize
        attrs['st_mtime'] = time()
    return attrs

def _put_bytes(radio, fname, buf, offset):

    def _file_put_msg(fname, buf, offset):
        # / <node_id> / "tag" / "sd" / 0 / devname / byte [/ fileno]
        tlv_list = fname
        tlv_list.extend([TagTlv(tlv_types.OFFSET, offset),
                         TagTlv(tlv_types.SIZE, len(buf))])
        tname = TagName(tlv_list)
        msg = TagPut(tname, pl=bytearray(buf))
        return msg.build()

    req_msg = _file_put_msg(fname, buf, offset)
    # zzz print(hexlify(req_msg))
    si446x_device_send_msg(radio, req_msg, RADIO_POWER);
    rsp_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, 5)
    if(rsp_msg):
        # zzz print(hexlify(rsp_msg))
        rsp = TagMessage(rsp_msg)
        # zzz print("{}".format(rsp.header.options.param.error_code))
        # zzz print(rsp.payload)
        file_rsp_pl_types = [tlv_types.SIZE,
                             tlv_types.ERROR,
        ]
        amt, error = file_payload2dict(rsp.payload,
                                       file_rsp_pl_types)
        # zzz print(amt, error)
        if (error == tlv_errors.SUCCESS):
            return len(buf) - amt
    return 0

def file_put_bytes(radio, devname, fileno, buf, offset):
    # / <node_id> / "tag" / "sd" / 0 / devname / byte [/ fileno]
    tlv_list = [TagTlv(tlv_types.NODE_ID, -1),
                TagTlv('tag'),
                TagTlv('sd'),
                TagTlv(0),
                TagTlv(devname.encode('ascii','ignore')),
                TagTlv('byte')]
    if (int(fileno)): tlv_list.append(TagTlv(tlv_types.INTEGER, int(fileno)))
    return _put_bytes(radio, tlv_list, buf, offset)

def dblk_put_note(radio, note):
    # / <node_id> / "tag" / "sd" / 0 / "dblk" / "note"
    tlv_list = [TagTlv(tlv_types.NODE_ID, -1),
                TagTlv('tag'),
                TagTlv('sd'),
                TagTlv(0),
                TagTlv('dblk'),
                TagTlv('note')]
    _put_bytes(radio, tlv_list, note, 0)
    return len(note)

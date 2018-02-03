# coding: utf-8

# Si446x Device Direct Access Byte File (Dblk and Panic)

from __future__ import print_function
from builtins import *                  # python3 types

__all__ = ['file_get_bytes',
           'file_put_bytes',
           'file_update_attrs',
           'dblk_put_note']

import os
import sys

from time import sleep
from time import time

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# zzz print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [basedir,
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print '\n'.join(sys.path)

from radioutils import payload2values, path2tlvs, path2list
#from radioutils import radio_send_msg, radio_receive_msg
from radioutils import msg_exchange

from tagnet import TagMessage, TagGet, TagPut, TagHead
from tagnet import TagName
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet import TlvListBadException, TlvBadException

# default paramters
#MAX_WAIT            = .3
#MAX_RECV            = 255
#MAX_PAYLOAD         = 254
#MAX_RETRIES         = 10
#RADIO_POWER         = 100
#SHORT_DELAY         = .02

def file_get_bytes(radio, path_list, amount_to_get, file_offset):
    '''
    File Byte Data Transfer function
    '''
    accum_bytes = bytearray()
    eof = False

    def _file_bytes_msg(path_list, amount_to_get, file_offset):
        # / <node_id> / "tag" / "sd" / 0 / devname / byte [/ fileno]
        tlv_list = path2tlvs(path_list)
        tlv_list.extend([TagTlv(tlv_types.OFFSET, file_offset),
                         TagTlv(tlv_types.SIZE, amount_to_get)])
        tname = TagName(tlv_list)
        # zzz
        print(tname)
        return TagGet(tname)

    accum_bytes = bytearray()
    tries = 3
    while (amount_to_get) and (tries):
        req_msg = _file_bytes_msg(path_list, amount_to_get, file_offset)
        # zzz print(req_msg.name)
        err, payload = msg_exchange(radio, req_msg)
        if (err == tlv_errors.SUCCESS):
            offset, amt2get, block = payload2values(payload,
                                                    [tlv_types.OFFSET,
                                                     tlv_types.SIZE,
                                                     tlv_types.BLOCK,
                                                    ])
            # zzz print('read pos: {}, len: {}, error: {}'.format(offset, amt2get, err))
            if (block):
                accum_bytes   += block
                file_offset   += len(block)
                amount_to_get -= len(block)
            if (eof):
                print('eof: {}'.format(offset))
                break
            if (offset) and (offset != file_offset):
                print('bad offset, expected: {}, got: {}'.format(
                    file_offset, offset))
                break
            if (amt2get) and (amt2get != amount_to_get):
                print('bad size, expected: {}, got: {}'.format(
                    amount_to_get, amt2get))
                break
        elif (err == tlv_errors.EBUSY):
            # zzz print('busy')
            continue
        elif (err == tlv_errors.EODATA):
            print('end of file, offset: {}'.format(offset))
            eof = True
            break
        else:
            print('unexpected error: {}, offset: {}'.format(err, offset))
            break
    # zzz
    print('read p/l:{}/{}'.format(file_offset-len(accum_bytes), len(accum_bytes)))
    return accum_bytes, eof

def file_update_attrs(radio, path_list, attrs):
    '''
    Retrieve current attributes of a file from remote tag
    '''

    def _file_attr_msg(path_list):
        tname = TagName(path2tlvs(path_list))
        # zzz print('file update attrs', path_list, tname)
        return TagHead(tname)

    req_msg = _file_attr_msg(path_list)
    if (req_msg == None):
        print('file_attr bad request msg')
        return attrs
    # zzz
    print(req_msg.name)
    err, payload = msg_exchange(radio, req_msg)
    if (err == tlv_errors.SUCCESS):
        this_time = time()
        print(payload)
        offset, filesize = payload2values(payload,
                                          [tlv_types.OFFSET,
                                           tlv_types.SIZE,
                                           # zzz tlv_types.UTC_TIME,
                                          ])
        if (filesize == None): filesize = 0
        if (offset == None): offset = 0
    else:
        print('file_attr error in response: {}'.format(err))
        this_time = time()
        filesize = 0
    attrs['st_size']  = filesize
    attrs['st_mtime'] = this_time
    return attrs

def _put_bytes(radio, tname, buf, offset):

    def _file_put_msg(tname, buf, offset):
        if (offset):
            tname.append(TagTlv(tlv_types.OFFSET, offset))
        msg = TagPut(tname, pl=bytearray(buf))
        return msg

    req_msg = _file_put_msg(tname, buf, offset)
    # zzz print(req_msg.name)
    err, payload = msg_exchange(radio, req_msg)
    if (err == tlv_errors.SUCCESS):
        amt = payload2values(payload,
                             [tlv_types.SIZE,
                             ])[0]
        if (amt == None): amt = 0
        # zzz
        print('put bytes', len(buf), amt)
        return amt
    # zzz
    print('put bytes', err)
    return 0

def file_put_bytes(radio, path_list, buf, offset):
    tname = TagName(path2tlvs(path_list))
    return _put_bytes(radio, tname, buf, offset)


def dblk_put_note(radio, path_list, note):
    tname = TagName(path2tlvs(path_list))
    return _put_bytes(radio, tname, note, 0)
#    return len(note)

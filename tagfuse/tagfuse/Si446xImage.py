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

__all__ = ['im_put_file',
           'im_get_file',
           'im_get_dir',
           'im_delete_file']

from Si446xDevice import *
from Si446xUtils import path2tlvs, name2version, payload2values, msg_exchange

sys.path.append("../tagnet")
from tagnet import TagMessage, TagGet, TagPut, TagHead, TagDelete
from tagnet import TagName
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet.tagtlv import TlvListBadException, TlvBadException

# default paramters
#MAX_WAIT            = 10
#MAX_RECV            = 255
#MAX_PAYLOAD         = 254
#MAX_RETRIES         = 10
#RADIO_POWER         = 100
#SHORT_DELAY         = 0

def im_put_file(radio, path_list, buf, offset):
    '''
    Write data to an image file on the Tag
    '''
    def _put_msg(path_list, buf, offset=None):
        tlv_list = path2tlvs(path_list)
        if (offset):
            tlv_list.append(TagTlv(tlv_types.OFFSET,
                                   offset))
        tname = TagName(tlv_list)
        msg = TagPut(tname)
        msg.payload = bytearray(buf[0:msg.payload_avail()])
        return (msg, len(msg.payload))

    amt_to_put = len(buf)
    while (amt_to_put):
        req_msg, amt_accepted = _put_msg(path_list,
                                         buf[(len(buf)-amt_to_put):],
                                         offset)
        print(req_msg)
        error, payload = msg_exchange(radio,
                                     req_msg)
        print(error, payload)
        if (error is not tlv_errors.SUCCESS):
            break
        if (payload[0].tlv_type() is tlv_types.OFFSET):
            prev_offset = offset
            offset = payload[0].value()
            amount_to_put -= offset - prev_offset
        else:
            offset += amt_accepted
            amount_to_put -= amt_accepted

    return error, offset

def im_get_file(radio, path_list, size, offset):
    return (None, None, None) # (error, buf, offset)

def im_get_dir(radio, path_list, version=None):
    '''
    Get Image Directory

    Returns a list of tuples containing a directory
    name and current state.
    '''
    # zzz print(path_list)

    def _get_dir_msg(path_list):
        im_name = TagName(path2tlvs(path_list))
        msg = TagGet(im_name)
        return msg

    dir_req = _get_dir_msg(path_list)
    # zzz print(dir_req.name)
    error, payload = msg_exchange(radio,
                                 dir_req)
    # zzz print(error, payload)
    rtn_list = []
    if (error == tlv_errors.SUCCESS):
        for x in range(0, len(payload), 2):
            version =  payload[x].value()
            state = payload[x+1].value()
            if (state != 'x'):
                if   (state == 'a'): state = 'active'
                elif (state == 'b'): state = 'backup'
                elif (state == 'g'): state = 'golden'
                elif (state == 'n'): state = 'NIB'
                elif (state == 'v'): state = 'valid'
                rtn_list.append((version, state))
    return rtn_list

def im_close_file(radio, path_list):
    def _close_msg(path_list):
        im_name = TagName(path2tlvs(path_list))
        msg = TagPut(im_name, pl=[TagTlv(tlv_types.EOF)])
        return msg

    close_req = _close_msg(path_list)
    # zzz
    print(close_req.name)
    error, payload = msg_exchange(radio,
                                 close_req)
    if (error) and (error != tlv_errors.SUCCESS):
        return False
    return True

def im_delete_file(radio):

    def _delete_msg(path_list, version):
        im_name = TagName(path2tlvs(path_list))
        msg = TagDelete(im_name)
        return msg

    delete_req = _delete_msg(path_list)
    # zzz
    print(delete_req.name)
    error, payload = msg_exchange(radio,
                                 delete_req)
    if (error) and (error != tlv_errors.SUCCESS):
        return False
    try:
        version =  payload[0].value()
        state   = payload[1].value()
        print("{}: state: {}, {}".format(rsp.header.options.param.error_code,
                                         state,
                                         version))
        return True
    except:
        return False

# coding: utf-8

# Si446x Device Direct Access Byte File (Dblk and Panic)

from __future__ import print_function
from builtins import *                  # python3 types

__all__ = ['im_put_file',
           'im_get_file',
           'im_get_dir',
           'im_delete_file',
           'im_close_file',
           'im_set_version',
           'show_radio_config',
]

import os
import sys

from time import time, sleep
from binascii import hexlify

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# zzz print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print '\n'.join(sys.path)

from radioutils import payload2values, path2tlvs, radio_show_config
from radioutils import msg_exchange, radio_send_msg, radio_receive_msg

from tagnet import TagMessage, TagGet, TagPut, TagHead, TagDelete
from tagnet import TagName
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet import TlvListBadException, TlvBadException

# default paramters
MAX_WAIT            = 1000 # milliseconds
MAX_RECV            = 2
MAX_PAYLOAD         = 254
MAX_RETRIES         = 4
RADIO_POWER         = 20
SHORT_DELAY         = 1000 # milliseonds

def show_radio_config(radio, config):
    '''
    Show Radio device configuration
    '''
    radio_show_config(radio.dump_radio())
    total = 0
    print('\n=== const config strings:')
    for s in config:
        print((hexlify(s)))
        total += len(s) - 4
    print('\n total: {}'.format(total))
    # ## Get Chip Status
    print(radio.get_chip_status())


def im_put_file(radio, path_list, buf, offset, power=RADIO_POWER, wait=MAX_WAIT):
    '''
    Write data to an image file on the Tag
    '''
    def _put_msg(path_list, buf, offset=None):
        tlv_list = path2tlvs(path_list[:-1])
        tlv_list.append(TagTlv(tlv_types.VERSION, path_list[-1].split('.')))
        if (offset):
            tlv_list.append(TagTlv(tlv_types.OFFSET,
                                   offset))
        tname = TagName(tlv_list)
        msg = TagPut(tname)
        msg.payload = bytearray(buf[0:msg.payload_avail()])
        return (msg, len(msg.payload))

    amt_to_put = len(buf)
    prev_offset    = offset
    tries = MAX_RETRIES
    while (amt_to_put > 0) and (tries > 0):
        req_msg, amt_sent = _put_msg(path_list,
                                     buf[(len(buf)-amt_to_put):],
                                     offset)
        # zzz
        print('im_put_file', req_msg.name)
        req_buf = req_msg.build()
        sstatus = radio_send_msg(radio, req_buf, power)
        rsp_buf, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, wait)
        rsp = None
        if (rsp_buf):
            try:
                rsp = TagMessage(bytearray(rsp_buf))
                # zzz print('msg_exchange',len(rsp_buf),hexlify(rsp_buf))
            except (TlvBadException, TlvListBadException):
                # zzz print('im_put_file, tries: ', tries)
                tries -=1
                continue
        if (rsp) and (rsp.payload):
            # zzz print('msg_exchange response', rsp.payload)
            error, offset = payload2values(rsp.payload,
                                           [tlv_types.ERROR,
                                            tlv_types.OFFSET,
                                           ])
            if error is None: error = tlv_errors.SUCCESS
            if ((error is tlv_errors.ERETRY) or
                (error is tlv_errors.EBUSY)):
                tries -= 1
            elif error is tlv_errors.SUCCESS:
                if (offset):
                    if (offset == prev_offset): # tag missed request
                        continue
                    elif offset < prev_offset: # not expected
                        error = tlv_errors.EINVAL
                        break
                    amt_to_put -= offset - prev_offset # move offset
                else:
                    amt_to_put  -= amt_sent
                    offset      += amt_sent
                    prev_offset  = offset
                tries = MAX_RETRIES
            else:
                break
        else:
            error = tlv_errors.ETIMEOUT
            tries -= 1
            print('msg_exchange: timeout', tries)
    return error, offset

def im_get_file(radio, path_list, size, offset):
    return (None, None, None) # (error, buf, offset)

def im_get_dir(radio, path_list, version=None):
    '''
    Get Image Directory

    Returns a list of tuples containing a directory
    name and current state.
    '''
    # zzz print('im_get_dir',path_list)

    def _get_dir_msg(path_list, version):
        tlv_list = path2tlvs(path_list)
        if (version):
            tlv_list.append(TagTlv(tlv_types.VERSION, version))
        im_name = TagName(tlv_list)
        msg = TagGet(im_name)
        return msg

    if (version):
        dir_req = _get_dir_msg(path_list, version)
    else:
        dir_req = _get_dir_msg(path_list, None)

    # zzz
    print('dir_req.name', dir_req.name)
    error, payload, msg_meta = msg_exchange(radio,
                                 dir_req)
    # zzz print(error, payload)
    rtn_list = []
    if (error == tlv_errors.SUCCESS):
        # zzz print(payload)
        for x in range(0, len(payload), 2):
            version =  payload[x].value()
            state = payload[x+1].value()
            # zzz print('im get dir, state: {} version: {}'.format(state,version))
            if   (state == 'a'): state = 'active'
            elif (state == 'b'): state = 'backup'
            elif (state == 'g'): state = 'golden'
            elif (state == 'n'): state = 'NIB'
            elif (state == 'v'): state = 'valid'
            rtn_list.append((version, state))
    return rtn_list

def im_close_file(radio, path_list, offset):

    def _close_msg(path_list):
        im_name = TagName(path2tlvs(path_list))
        im_name.append(TagTlv(tlv_types.OFFSET, offset))
        msg = TagPut(im_name, pl=TagTlvList([TagTlv(tlv_types.EOF)]))
        return msg

    close_req = _close_msg(path_list)
    # zzz
    print('im close file', close_req.name, close_req.payload)
    error, payload, msg_meta = msg_exchange(radio,
                                 close_req)
    print('im close file',error,payload)
    if (error) \
       and (error != tlv_errors.SUCCESS) \
       and (error != tlv_errors.EODATA):
        return 0
    offset = payload2values(payload,
                            [tlv_types.OFFSET,
                            ])[0]
    if (offset):
        return offset
    else:
        return 0

def im_delete_file(radio, path_list):
    """
    Delete the file from the remote tag

    Return True  if error == success
    """
    def _delete_msg(path_list):
        im_name = TagName(path2tlvs(path_list))
        msg = TagDelete(im_name)
        return msg

    # zzz
    print('im_delete_file', path_list)
    delete_req = _delete_msg(path_list)
    # zzz
    print(delete_req.name)
    error, payload, msg_meta = msg_exchange(radio,
                                 delete_req)
    print(payload)
    if (error) and (error != tlv_errors.SUCCESS):
        error = tlv_errors.SUCCESS
    print(error)
    return error


def im_set_version(radio, path_list):

    def _set_version_msg(path_list):
        tlv_list = path2tlvs(path_list[:-1])
        tlv_list.append(TagTlv(tlv_types.VERSION, path_list[-1].split('.')))
        req_obj = TagPut(TagName(tlv_list))
        return req_obj

    req_msg = _set_version_msg(path_list)
    print('im_set_version', req_msg.name)
    err, payload, msg_meta = msg_exchange(radio, req_msg)
    if (err is None):
        err = tlv_errors.SUCCESS
    print(err)
    return err

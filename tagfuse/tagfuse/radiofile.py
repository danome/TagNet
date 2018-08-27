# coding: utf-8

# Si446x Device Direct Access Byte File (Dblk and Panic)

from __future__ import print_function
from builtins import *                  # python3 types

__all__ = ['file_get_bytes',
           'file_put_bytes',
           'file_update_attrs',]

import os
import sys

from time import sleep
from time import time
import structlog
logger = structlog.getLogger('fuse.log-mixin.' + __name__)
mylog = logger.bind(scope=__name__)
import inspect

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

try:
    from radioutils import payload2values, path2tlvs, path2list
    from radioutils import msg_exchange
    from tagfuseargs import get_cmd_args
except ImportError:
    from tagfuse.radioutils import payload2values, path2tlvs, path2list
    from tagfuse.radioutils import msg_exchange
    from tagfuse.tagfuseargs import get_cmd_args

from tagnet import TagMessage, TagGet, TagPut, TagHead, TagPoll
from tagnet import TagName
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet import TlvListBadException, TlvBadException


def file_get_bytes(radio, path_list, amount_to_get, file_offset):
    '''
    File Byte Data Transfer function
    '''
    accum_bytes = bytearray()
    eof = False

    def _file_bytes_msg(path_list, amount_to_get, file_offset):
        # / <node_id> / "tag" / "sd" / 0 / blockname / byte [/ fileno]
        tlv_list = path2tlvs(path_list)
        tlv_list.extend([TagTlv(tlv_types.OFFSET, file_offset),
                         TagTlv(tlv_types.SIZE, amount_to_get)])
        tname = TagName(tlv_list)
        if get_cmd_args().verbosity > 2:
            mylog.debug(method=inspect.stack()[0][3], name=tname)
        return TagGet(tname)

    end = time() + DEADMAN_TIME # deadman timer
    accum_bytes = bytearray()
    eof = False
    while (amount_to_get) and time() < end:
        req_msg = _file_bytes_msg(path_list, amount_to_get, file_offset)
        mylog.debug(method=inspect.stack()[0][3], name=req_msg.name)
        err, payload, msg_meta = msg_exchange(radio, req_msg)
        if get_cmd_args().verbosity > 3:
            mylog.debug(method=inspect.stack()[0][3],
                           error=err,
                           data=payload)
        if (err == tlv_errors.SUCCESS) or \
           (err == tlv_errors.EODATA):
            offset, amt2get, block = payload2values(payload,
                                                    [tlv_types.OFFSET,
                                                     tlv_types.SIZE,
                                                     tlv_types.BLOCK,
                                                    ])
            if get_cmd_args().verbosity > 2:
                mylog.debug(method=inspect.stack()[0][3],
                               offset=offset,
                               count=amt2get,
                               size=len(block),
                               error=err)
            if (block):
                accum_bytes   += block
                file_offset   += len(block)
                amount_to_get -= len(block)
            if (err == tlv_errors.EODATA):
                mylog.info('end of data',
                           method=inspect.stack()[0][3],
                           offset=file_offset,
                           count=amount_to_get,
                           error=err)
                eof = True
                break

            if (offset) and (offset != file_offset):
                mylog.info('offset mismatch',
                           method=inspect.stack()[0][3],
                           offset=file_offset,
                           size=offset)
                break
            if (amt2get) and (amt2get != amount_to_get):
                mylog.info('size mismatch',
                           method=inspect.stack()[0][3],
                           size=amount_to_get,
                           count=amt2get)
                break
        elif (err == tlv_errors.EBUSY):
            mylog.info('busy',
                       method=inspect.stack()[0][3],
                       offset=file_offset,
                       error=err)
            continue
        else:
            mylog.info('unexpected', method=inspect.stack()[0][3],
                           offset=file_offset,
                           error=err)
            break
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3],
                    count=file_offset-len(accum_bytes),
                    size=len(accum_bytes),
                    eof=eof)
    return accum_bytes, eof

def file_update_attrs(radio, path_list, attrs):
    '''
    Retrieve current attributes of a file from remote tag
    '''

    def _file_attr_msg(path_list):
        tname = TagName(path2tlvs(path_list))
        return TagHead(tname)

    req_msg = _file_attr_msg(path_list)
    if (req_msg == None):
        mylog.info('bad request',
                   method=inspect.stack()[0][3],
                   path=path_list)
        return attrs
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3],
                    name=req_msg.name)
    err, payload, msg_meta = msg_exchange(radio, req_msg)
    if (err == tlv_errors.SUCCESS):
        if get_cmd_args().verbosity > 2:
            mylog.debug(method=inspect.stack()[0][3],
                        data=payload)
        offset, filesize = payload2values(payload,
                                          [tlv_types.OFFSET,
                                           tlv_types.SIZE,
                                           # zzz tlv_types.UTC_TIME,
                                          ])
        this_time = time() # zzz need to set from response value
        if (filesize == None): filesize = 0
        if (offset == None): offset = 0
    else:
        mylog.info('failure', method=inspect.stack()[0][3], error=err)
        this_time = -1
        filesize = 0
    attrs['st_size']  = filesize
    attrs['st_mtime'] = this_time
    return attrs

def _put_bytes(radio, tname, buf, offset):
    '''
    Send bytes to a remote file on the tag
    '''

    def _file_put_msg(tname, buf, offset):
        if (offset):
            tname.append(TagTlv(tlv_types.OFFSET, offset))
        msg = TagPut(tname, pl=bytearray(buf))
        return msg

    req_msg = _file_put_msg(tname, buf, offset)
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3],
                    name=req_msg.name)
    err, payload, msg_meta = msg_exchange(radio, req_msg)
    if (err == tlv_errors.SUCCESS):
        amtLeft = payload2values(payload,
                             [tlv_types.SIZE,
                             ])[0]
        if (amtLeft == None):
            amtLeft = len(buf)
        if get_cmd_args().verbosity > 2:
            mylog.debug(method=inspect.stack()[0][3],
                        count=len(buf),
                        size=amtLeft)
        return amtLeft
    mylog.info(method=inspect.stack()[0][3], error=err)
    return 0

def file_put_bytes(radio, path_list, buf, offset):
    tname = TagName(path2tlvs(path_list))
    return _put_bytes(radio, tname, buf, offset)

mylog.debug('initiialization complete')

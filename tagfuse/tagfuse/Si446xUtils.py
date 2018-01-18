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
import re
from collections import defaultdict, OrderedDict
from time import time

__all__ = ['name2version',
           'payload2values',
           'msg_exchange',
           'show_radio_config',
           'si446x_device_enable',
           'file_payload2dict',
           'path2tlvs']

from Si446xDevice import *

sys.path.append("../tagnet")
from tagnet import TagMessage, TagGet, TagPut, TagHead
from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet.tagtlv import TlvListBadException, TlvBadException

# default paramters
MAX_WAIT            = .4
MAX_RECV            = 255
MAX_PAYLOAD         = 254
MAX_RETRIES         = 10
RADIO_POWER         = 100
SHORT_DELAY         = 0

def name2version(name):
    '''
    convert file name to tuple of version (major,minor,build)
    return name.split('.')
    '''

def payload2values(payload, keynames):
    '''
    Extract all parameters in payload and then filter for the
    parameters of interest.

    Remove any matched parameters from the payload.
    '''
    plist = []
    for match_key in keynames:
        for tlv in payload:
            if match_key == tlv.tlv_type():
                plist.append(tlv.value())
                payload.remove(tlv)
            else:
                plist.append(None)
            print(match_key, tlv, plist)
    print(plist)
    return (plist)

def path2tlvs(path_list):
    '''
    Convert a list of individual elements in a path into
    a list of Tag Tlvs
    '''
    def _build_tlv(val):
        try:
            key, value = re.findall('<(.{1,}):(.{1,})>', val)[0]
            # zzz print(key, value)
            return TagTlv(eval('tlv_types.'+key.upper()),
                          eval(value))
        except: pass
        try:
            return TagTlv(tlv_types.INTEGER, int(val))
        except: pass
        try:
            return TagTlv(tlv_types.STRING, bytearray(val.encode('utf-8')))
        except: pass
        return None

    tlist = []
    for p in path_list:
        t = _build_tlv(p)
        if (t):
            tlist.append(t)
    return tlist

def msg_exchange(radio, req):
    '''
    Send a TagNet request msg and wait for a response.

    checks for error in response and will retry three times
    if request was not successful.
    Timeouts on the transmit will also be counted as an error
    and reported appropriately.
    '''
    tries = 3
    req_msg = req.build()
    # zzz print(len(req_msg),hexlify(req_msg))
    while (tries):
        error = tlv_errors.ERETRY
        payload = None
        si446x_device_send_msg(radio,
                               req_msg,
                               RADIO_POWER);
        rsp_buf, rssi, status = si446x_device_receive_msg(radio,
                                                          MAX_RECV,
                                                          MAX_WAIT)
        if (rsp_buf):
            # zzz print(len(rsp_buf),hexlify(rsp_buf))
            try:
                rsp = TagMessage(rsp_buf)
            except:
                print("can't decode: {}".format(hexlify(rsp_buf)))
                continue
            if (rsp.payload):
                # zzz print(rsp.payload)
                if (rsp.payload[0].tlv_type() is tlv_types.ERROR):
                    error = rsp.payload[0].value()
                    del rsp.payload[0]
                else:
                    error = tlv_errors.SUCCESS
                if (error is tlv_errors.SUCCESS):
                    payload = rsp.payload
                    tries = 1
            # zzz print(tries)
        else:
            error = tlv_errors.ETIMEOUT
            print('timeout')
        tries -= 1
    return error, payload

def show_radio_config(radio, config):
    '''
    Show Radio device configuration
    '''
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
    '''
    Start up Radio
    '''
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
    # zzz  print(dfile)
    plist = []
    for item in keynames:
        try:
            plist.append(dfile[item])
        except:
            plist.append(None)
    return plist

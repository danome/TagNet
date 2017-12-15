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


def _dblk_request_msg(amount_to_get, file_offset):
    # / "tag" / "sd" / <node_id> / "0" / "dblk" / "0"
    dblk_bytes_name = TagName ('/tag/sd')
    dblk_bytes_name += [TagTlv(tlv_types.NODE_ID, -1),
                        TagTlv(0),
                        TagTlv('dblk'),
                        TagTlv(0),
                        TagTlv(tlv_types.OFFSET, file_offset),
                        TagTlv(tlv_types.SIZE, amount_to_get),
                       ]
    get_dblk = TagGet(dblk_bytes_name)
#    print(get_dblk.name)
    return get_dblk.build()

def dblk_payload2dict(payload):
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
    for item in [tlv_types.OFFSET, tlv_types.SIZE, tlv_types.BLOCK, tlv_types.EOF, tlv_types.ERROR]:
        try:
            plist.append(ddblk[item])
        except:
            plist.append(None)
    return plist


def get_dblk_bytes(radio, amount_to_get, file_offset):
    '''
    Dblk Byte Data Transfer function
    '''
    accum_bytes = bytearray()
    while (amount_to_get):
        req_msg = _dblk_request_msg(amount_to_get, file_offset)
        si446x_device_send_msg(radio, req_msg, RADIO_POWER);
        rsp_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, 5)
        if(rsp_msg):
#            print(hexlify(rsp_msg))
            rsp = TagMessage(rsp_msg)
#            print("{}".format(rsp.header.options.param.error_code))
            #        print(rsp.payload)
            offset, amt2get, block, eof, err = dblk_payload2dict(rsp.payload)
            print('offset: {}, amount remaining: {}'.format(offset, amt2get))
            if (block):
                accum_bytes   += block
                file_offset   += len(block)
                amount_to_get -= len(block)
            if (err):
                if (err == tlv_errors.EBUSY):
#                    print('busy')
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
    print()
    return accum_bytes, eof

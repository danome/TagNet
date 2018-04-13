# coding: utf-8

# Si446x Device Direct Access Layer Access
#
# This notebook explores the Si446xRadio class, which handles the direct access to operating system provided SPI bus and GPIO interface pins that connect to the Si446x device. This provides the command and control interface provided by the device.

from __future__ import print_function
from builtins import *                  # python3 types

UNIT_TESTING = False

__all__ = ['name2version',
           'payload2values',
           'msg_exchange',
           'path2tlvs',
           'path2list',
           'radio_start',
           'radio_config',
           'radio_get_group',
           'radio_get_property',
           'radio_format_group',
           'radio_show_config',
           'radio_get_raw_config',
           'radio_receive_msg',
           'radio_send_msg',
           'radio_get_position',
           'radio_get_rssi',
           'radio_get_power',
           'radio_set_power',
           'radio_read_test',
           'radio_write_test',
           'radio_poll',
           'radio_get_rtctime',
           'radio_set_rtctime',
]

import sys
import os

from datetime import datetime, timedelta
from time import sleep
import struct as pystruct
import types
from binascii import hexlify

from pyproj import Proj, transform


# If we are running from the source package directory, try
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

from si446x import Si446xRadio
from si446x import clr_pend_int_s
from si446x import radio_config_cmd_ids, radio_config_commands
from si446x import radio_config_group_ids, radio_config_groups
from si446x import radio_display_structs, RadioTraceIds

from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet import TagMessage, TagName
from tagnet import TagPoll, TagGet, TagPut, TagDelete, TagHead
from tagnet import TlvListBadException, TlvBadException

clr_all_flags = clr_pend_int_s.parse('\00' * clr_pend_int_s.sizeof())
clr_no_flags  = clr_pend_int_s.parse('\ff' * clr_pend_int_s.sizeof())

# default paramters
MAX_FIFO_SIZE = 64
MAX_WAIT            = 1
MAX_RECV            = 2
MAX_PAYLOAD         = 254
MAX_RETRIES         = 3
RADIO_POWER         = 20
SHORT_DELAY         = 1


#WGS84   EPSG:4326     World Geodetic System 1984 (lat/lon)
#ECEF    EPSG:4978     SirfBin X.Y.Z
#        EPSG:3857     ??? Psuedo-Mercator Google Maps
wgs84= Proj(init='epsg:4326')
ecef = Proj(init='epsg:4978')
psdo = Proj(init='epsg:3857')

#(gdb) p GPSmonitorP__m_xyz
#$7 = {ts = 0x229927d, tow = 0x2ee8d04, x = 0xffd6c1bf, y = 0xffbe1099, z = 0x3a5104,
#           week = 0x3b4, mode1 = 0x4, hdop = 0x4, nsats = 0x8}
#(gdb) p GPSmonitorP__m_geo
#$8 = {ts = 0x2299260, tow = 0x1d518228, week_x = 0x7b4, nsats = 0x8, additional_mode = 0x18,
#           lat = 0x16153920, lon = 0xb7443e55, sat_mask = 0x51084812, nav_valid = 0x0,
#           nav_type = 0x204, ehpe = 0x377, evpe = 0x0, alt_ell = 0x3eaf, alt_msl = 0x4905,
#           sog = 0x0, cog = 0x6665, hdop = 0x4}
xyz_struct = pystruct.Struct('>iii')
lata = "16153920"
lona = "b7443e55"
elva = "00003eaf"
ba=bytearray.fromhex(lata+lona+elva)
lat, lon, elv = xyz_struct.unpack(ba)

home_geo = float(lat)/10**7, float(lon)/10**7, float(elv)/10**2
print(lat,lon,elv,(hex(lat),hex(lon),hex(elv)))

xa = "ffd6c1bf"
ya = "ffbe1099"
za = "003a5104"
ba=bytearray.fromhex(xa+ya+za)
x, y, z = xyz_struct.unpack(ba)

home_xyz = x, y, z
print(x,y,z,(hex(x),hex(y),hex(z)))

# Scotts Valley
# x: -13583956.319900 y: 4445954.972893
# lat: 37°2'56.813" lon: -122°1'36.321"
# lat: 37.0491147°  lon: -122.0267558°


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
    # zzz print('keynames', keynames)
    for match_key in keynames:
        item = None
        for tlv in payload:
            if match_key == tlv.tlv_type():
                item = tlv.value()
                payload.remove(tlv)
                break
            # zzz print('for tlv', match_key, tlv, plist)
        plist.append(item)
    # zzz print('plist', plist)
    return (plist)

def path2tlvs(path_list):
    '''
    Convert a list of individual elements in a path into
    a list of Tag Tlvs
    '''
    def _build_tlv(val):
        try:                                   # integer
            return TagTlv(tlv_types.INTEGER, int(val))
        except: pass
        try:                                   # string or <type:value>
            return TagTlv(val.encode('utf-8'))
        except: pass
        return TagTlv(val)

    tlist = []
    for p in path_list:
        t = _build_tlv(p)
        if (t):
            tlist.append(t)
    return tlist

def path2list(path):
    path = os.path.abspath(os.path.realpath(path))
    return path.split('/')[1:]

def msg_exchange(radio, req):
    '''
    Send a TagNet request msg and wait for a response.

    checks for error in response and will retry three times
    if request was not successful.
    Timeouts on the transmit will also be counted as an error
    and reported appropriately.
    '''
    req_msg = req.build()
    # zzz print(len(req_msg),hexlify(req_msg))
    tries = 3
    while (tries):
        error = tlv_errors.ERETRY
        payload = None
        radio_send_msg(radio, req_msg, RADIO_POWER);
        rsp_buf, rssi, status = radio_receive_msg(radio, MAX_RECV, MAX_WAIT)
        if (rsp_buf):
            # zzz print(len(rsp_buf),hexlify(rsp_buf))
            try:
                rsp = TagMessage(bytearray(rsp_buf))
                if (rsp.payload):
                    # zzz print('msg exchange response', rsp.payload)
                    payload = rsp.payload
                    error, eof = payload2values(rsp.payload,
                                           [tlv_types.ERROR,
                                            tlv_types.EOF,
                                           ])
                    if (error is None):
                        error = tlv_errors.SUCCESS
                    if (eof):
                        error = tlv_errors.EODATA
                    if (error is tlv_errors.EODATA) \
                       or (error is tlv_errors.EALREADY) \
                       or (error is tlv_errors.SUCCESS):
                        tries = 1
                # zzz print('msg_exchange, tries: ', tries)
            except (TlvBadException, TlvListBadException):
                pass
        else:
            error = tlv_errors.ETIMEOUT
            print('msg_exchange: timeout')
        tries -= 1
    return error, payload

def radio_config(radio):
    '''
    Configure Si446x Radio

    Uses the pre-compiled config string lists as well as some
    additional configuration.
    '''
    radio.config_frr()
    config_strings = []
    list_of_lists = radio.get_config_lists()
    for l in list_of_lists:
        x = 0
        while (True):
            s = l(x)
            x += len(s) + 1
            if (not s): break
            if s[0] == radio_config_cmd_ids.build('POWER_UP'): continue
            if s[0] == radio_config_cmd_ids.build('SET_PROPERTY'):
                if s[1] == radio_config_group_ids.build('FRR_CTL'):
                    continue
            config_strings.append(s)
            radio.send_config(s)
            status = radio.get_chip_status()
            if (status.chip_pend.CMD_ERROR):
                print(status)
                print(insert_space(s))
                radio.clear_interrupts()
    # these settings should be included in the compiled config strings
    radio.set_property('PKT', 0x0b, '\x10\x10') # tx/rx threshold
    return config_strings

def radio_show_config(radio, config):
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

def radio_start():
    '''
    Start up Radio
    '''
    radio=Si446xRadio(0)
    if (radio == None):
        print('radio_start: could not instantiate radio')
    radio.unshutdown()
    radio.power_up()
    # Check for Command Error
    status = radio.get_chip_status()
    if (status.chip_pend.CMD_ERROR):
        print(status)
    # Configure Radio
    config = radio_config(radio)
    status = radio.get_chip_status()
    if (status.chip_pend.CMD_ERROR):
        print(status)
#    radio_show_config(radio, config)
    return radio

# Get Radio Property Group

def radio_get_group(radio, g_n):
    g_s = radio_config_groups[radio_config_group_ids.build(g_n)]
    return g_s.parse(radio_get_property(radio, g_n, 0, g_s.sizeof()))


# Get Radio Property

def radio_get_property(radio, g_n, start, limit):
    prop_x = 0
    prop_b = bytearray()
    while (prop_x < limit):
        chunk_size = limit - prop_x
        x = MAX_RADIO_RSP if (chunk_size >= MAX_RADIO_RSP) else chunk_size
        rsp = radio.get_property(g_n, prop_x, x)
        if (rsp):
            prop_b += bytearray(rsp[:x])
            prop_x += x
        else:
            return None
    return prop_b


# Format Radio Property Group

def radio_format_group(gn, data):
    s = ' {} '.format(gn)
    try:
        my_struct = radio_config_groups[radio_config_group_ids.build(gn)]
        p = radio_display_structs[my_struct]
        s += p(my_struct, data)
    except:
        if ((s_name == 'string') or isinstance(data, types.StringType)):
            s += data
        else:
            s += insert_space(hexlify(data))
    return  s


#  Show Radio Configuration

def radio_show_config(config):
    total = 0
    for k, v in config.iteritems():
        total += len(v)
        s = radio_config_groups[k]
        p = radio_display_structs[s]
        print('\n{}: {}\n{}'.format(s.name, s.sizeof(), insert_space(v)))
        print(p(s,v))
    print('\n=== total: {}'.format(total))


# Get Compiled Radio Configuration

def radio_get_raw_config():
    rl = []
    for l in [get_config_wds, get_config_device]:
        x = 0
        while (True):
            s = l(x)
            if (not s): break
            rl.append(s)
            x += len(s) + 1
    return rl


# Get Radio Interrupt Information

def int_status(radio, clr_flags=None, show=False):
    clr_flags = clr_flags if (clr_flags) \
                else clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    clr_flags.ph_pend.STATE_CHANGE = False    # always clear this interrupt
    p_g = radio.get_clear_interrupts(clr_flags)
    if (show is True):
        s_name =  'int_status_rsp_s'
        p_s = eval(s_name)
        p_d = p_s.build(p_g)
#        print('{}: {}'.format(s_name, hexlify(p_d)))
        print(radio_display_structs[p_s](p_s, p_d))
    return p_g


def show_int_rsp(radio, pend_flags):
    s_name =  'int_status_rsp_s'
    p_s = eval(s_name)
    clr_flags = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    clr_flags.ph_pend.STATE_CHANGE = False
    p_g = radio.get_clear_interrupts(clr_flags)
    p_d = p_s.build(p_g)
#    print('{}: {}'.format(s_name, hexlify(p_d)))
    print(radio_display_structs[p_s](p_s, p_d))


def msg_chunk_generator(radio, msg):
    index = 0
    while True:
        status = []
        __, tx_len = radio.fifo_info()
        tranche = index
        if (tx_len > 0):
            tranche = len(msg[index:]) if (len(msg[index:]) < tx_len) else tx_len
        yield msg[index:index+tranche], ['c',str(tx_len),',',str(tranche)]
        index += tranche


def radio_send_msg(radio, msg, pwr):
    progress = []
    show_flag = False

    msg_chunk = msg_chunk_generator(radio, msg)

    int_status(radio, clr_all_flags, show_flag)
    radio.set_power(pwr)

    __, tx = radio.fifo_info(rx_flush=True, tx_flush=True)
    if (tx != MAX_FIFO_SIZE): print('tx fifo bad: {}'.format(tx))

    chunk, p = msg_chunk.next()
    progress.extend(p)
    radio.write_tx_fifo(chunk)
    radio.start_tx(len(msg))

    cflags = clr_no_flags
    while (True):
        status = int_status(radio, cflags, show_flag)
        cflags = clr_no_flags
        no_action = True
        if (status.chip_pend.CMD_ERROR):
            cflags.chip_pend.CMD_ERROR = False
            no_action = False
            progress.append('E')
            break
        elif (status.ph_pend.TX_FIFO_ALMOST_EMPTY):
            cflags.ph_pend.TX_FIFO_ALMOST_EMPTY = False
            no_action = False
            chunk, p = next(msg_chunk)
            progress.extend(p)
            if (len(chunk)):
                radio.write_tx_fifo(chunk)
        elif (status.ph_pend.PACKET_SENT):
            cflags.ph_pend.PACKET_SENT = False
            no_action = False
            rx, tx = radio.fifo_info()
            progress.extend(['f', str(tx)])
            break
        elif (status.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR):
            cflags.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR = False
            no_action = False
            progress.extend(['U', status.ph_pend, '-', status.modem_pend, '-', status.chip_pend])
            break
        if (no_action):
            progress.append('w')

    progress.extend([':', len(msg)])
#    status = int_status(radio, clr_all_flags)

    if (status.chip_pend.CMD_ERROR):
        print('radio send command error',status)
        print(progress)
        status = int_status(radio, clr_all_flags)

    return progress


# Receive a complete message

def drain_rx_fifo(radio, p):
    rx_len, __ = radio.fifo_info()
    if (rx_len > MAX_FIFO_SIZE):
        rx_len = MAX_FIFO_SIZE
        p.append('?')
    p.append(rx_len)
#    rx = 0  # force the fifo read to fail to verify overrun error
    if (rx_len): return bytearray(radio.read_rx_fifo(rx_len))
    else:    return ''

def radio_receive_msg(radio, max_recv, wait):
    start = datetime.now()
    delta= timedelta(seconds=wait)
    end = start + delta
    msg = bytearray()
    progress = []
    show = False
    rssi = -1
    int_status(radio, clr_all_flags)
    radio.fifo_info(rx_flush=True, tx_flush=True)
    radio.start_rx(0)
    status = int_status(radio, clr_no_flags)
    while (datetime.now() < end):
        cflags = clr_no_flags
        if (status.modem_pend.INVALID_PREAMBLE):
            cflags.modem_pend.INVALID_PREAMBLE = False
            if (not progress):
                progress.append('p')
            elif progress[-1] == 'p':
                progress.append(2)
            elif (isinstance(progress[-1], (int, long))) and (progress[-2] == 'p'):
                progress[-1] += 1
            else:
                progress.append('p')
        if (status.modem_pend.INVALID_SYNC):
            cflags.modem_pend.INVALID_SYNC = False
            progress.append('s')
        if (status.ph_pend.RX_FIFO_ALMOST_FULL):
            cflags.ph_pend.RX_FIFO_ALMOST_FULL = False
            progress.append('w')
            msg += drain_rx_fifo(radio, progress)
            progress.append('.')
            rx, tx = radio.fifo_info()
            progress.append(rx)
        if (status.ph_pend.PACKET_RX):
            rssi = radio.fast_latched_rssi()
            cflags.ph_pend.PACKET_RX = False
            progress.append('f')
            msg += drain_rx_fifo(radio, progress)
            progress.append('.')
            rx, tx = radio.fifo_info()
            progress.append(rx)
            progress.append(':')
            progress.append(len(msg))
            break
        if (status.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR):
            cflags.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR = False
            break
        if (status.chip_pend.CMD_ERROR):
            cflags.chip_pend.CMD_ERROR = False
            print('radio receive cmd error')
            break
        status = int_status(radio, cflags, show)
    status = int_status(radio)
    pkt_len = radio.get_packet_info()
    if (datetime.now() > end):
        progress.extend(['to','e'])
    elif ((pkt_len + 1) != len(msg)):
        progress.extend(['e', pkt_len + 1,',',len(msg),'e'])

    if (status.chip_pend.CMD_ERROR):
        print('radio receive command error', status)
        print(progress)

    return (msg, rssi, progress)


def radio_poll(radio):
    req_obj = TagPoll() # sends time, slot_time, slot_count, node_id, node_name
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, RADIO_POWER)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, 3)
    if rsp_msg:
        #        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
        #        print(rsp_obj.header.options.param.error_code)
        #        print(rsp_obj.payload)
        # print(rsp_obj.header, rsp_obj.name)
        if rsp_obj.payload:
            return rsp_obj.payload, rssi, sstatus, rstatus
        return none, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_get_position(radio, node=None, name=None):
    gps_geo = None
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        get_name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('info'),
                            TagTlv('sens'),
                            TagTlv('gps'),
                            TagTlv('xyz')])
    xyz_struct = pystruct.Struct('<iii')
    get_gps_xyz = TagGet(get_name)
#    print(get_gps_xyz.name)
    req_msg = get_gps_xyz.build()
    s_status = radio_send_msg(radio, req_msg, RADIO_POWER);
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, MAX_WAIT)
    if(rsp_msg):
#        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
#        print(rsp_obj.header.options.param.error_code)
        print(rsp_obj.payload)
        if (rsp_obj.payload):
#            print("{}: {}".format(rsp_obj.header.options.param.error_code, rsp_obj.payload[0]))
            gps_xyz = rsp_obj.payload[0].value()
#            print("x:{0}, y:{1}, z:{2}".format(*gps_xyz))
            lon, lat, elv = transform(ecef, wgs84, *gps_xyz)
            gps_geo = float(lat), float(lon), float(elv)
            # print("lat:{0}, lon:{1}, elv:{2}".format(*gps_geo))
            return gps_xyz, gps_geo
        else:
            print("{}".format(rsp_obj.header.options.param.error_code))
    else:
        print('TIMEOUT')
    return None


def radio_get_rssi(radio, node=None, name=None):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        get_name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv('rssi')])
    req_obj = TagGet(get_name)
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, RADIO_POWER)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, 3)
    if rsp_msg:
        #        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
        #        print(rsp_obj.header.options.param.error_code)
        #        print(rsp_obj.payload)
        # print(rsp_obj.header, rsp_obj.name)
        if rsp_obj.payload:
            return rsp_obj.payload[0].value(), rssi, sstatus, rstatus
        return None, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_get_power(radio, node=None, name=None):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        get_name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv('tx_pwr')])
    req_obj = TagGet(get_name)
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, RADIO_POWER)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, 3)
    if rsp_msg:
        #        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
        #        print(rsp_obj.header.options.param.error_code)
        #        print(rsp_obj.payload)
        #print(rsp_obj.header, rsp_obj.name)
        #if rsp_obj.payload:
        #    print(rsp_obj.payload)
        return rsp_obj.payload[0].value(), rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_set_power(radio, power, node=None, name=None):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        get_name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv('tx_pwr'),])
    req_obj = TagPut(get_name,
                     pl=TagTlvList([TagTlv(tlv_types.INTEGER,
                                           power)]))
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, RADIO_POWER)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, 3)
    if rsp_msg:
        #        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
        #        print(rsp_obj.header.options.param.error_code)
        #        print(rsp_obj.payload)
        #print(rsp_obj.header, rsp_obj.name)
        #if rsp_obj.payload:
        #    print(rsp_obj.payload)
        return rsp_obj.payload, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_get_rtctime(radio, node=None, name=None):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        get_name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('sys'),
                            TagTlv('rtc')])
    req_obj = TagGet(get_name)
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, RADIO_POWER)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, 3)
    if rsp_msg:
        print(len(rsp_msg), hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
        #        print(rsp_obj.header.options.param.error_code)
        #        print(rsp_obj.payload)
        #print(rsp_obj.header, rsp_obj.name)
        #if rsp_obj.payload:
        #    print(rsp_obj.payload)
        return rsp_obj.payload[0].value(), rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_set_rtctime(radio, utctime, node=None, name=None):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                        TagTlv('tag'),
                        TagTlv('sys'),
                        TagTlv('rtc'),])
    req_obj = TagPut(name,
                     pl=TagTlvList([TagTlv(tlv_types.UTC_TIME,
                                           utctime)]))
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, RADIO_POWER)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, 3)
    if rsp_msg:
        #        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
        #        print(rsp_obj.header.options.param.error_code)
        #        print(rsp_obj.payload)
        #print(rsp_obj.header, rsp_obj.name)
        #if rsp_obj.payload:
        #    print(rsp_obj.payload)
        return rsp_obj.payload, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


#<node_id>   "tag"  "test"   "zero"   "byte"
def radio_read_test(radio, test_name, pos, num, node=None, name=None):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        get_name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv(test_name),
                            TagTlv('byte'),
                            TagTlv(tlv_types.OFFSET, pos),
                            TagTlv(tlv_types.SIZE, num),])
    req_obj = TagGet(get_name)
#    print(get_gps_xyz.name)
    req_msg = req_obj.build()
    radio_send_msg(radio, req_msg, RADIO_POWER);
    rsp_msg, rssi, status = radio_receive_msg(radio, MAX_RECV, MAX_WAIT)
    if rsp_msg:
#        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
#        print(rsp_obj.header.options.param.error_code)
#        print(rsp_obj.payload)
        if rsp_obj.payload:
            error, offset, amt, block = payload2values(rsp_obj.payload,
                                  [tlv_types.ERROR,
                                   tlv_types.OFFSET,
                                   tlv_types.SIZE,
                                   tlv_types.BLOCK,
                                  ])
            seta = set(block)
            # print(seta)
            if (len(seta) > 1):
                print('check error', seta, amt, hexlify(block))
                amt = 0
            return error, offset, amt, block
        else:
            print("{}".format(rsp_obj.header.options.param.error_code))
#    else:
#        print('TIMEOUT')
    return None


def radio_write_test(radio, test_name, buf, node=None, name=None):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        get_name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv(test_name),
                            TagTlv('byte'),
                            TagTlv(tlv_types.OFFSET, 0),
                            TagTlv(tlv_types.SIZE, len(buf)),])
    req_obj = TagPut(get_name, pl=buf)
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, RADIO_POWER)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, 3)
    if rsp_msg:
        #        print(hexlify(rsp_msg))
        rsp_obj = TagMessage(rsp_msg)
        #        print(rsp_obj.header.options.param.error_code)
        #        print(rsp_obj.payload)
        # print(rsp_obj.header, rsp_obj.name)
        if rsp_obj.payload:
            return rsp_obj.payload[0].value(), rssi, sstatus, rstatus
        return none, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


# # UNIT TEST

def insert_space(st):
    p_ds = ''
    ix = 4
    i = 0
    p_s = hexlify(st)
    while (i < (len(st) * 2)):
        p_ds += p_s[i:i+ix] + ' '
        i += ix
    return p_ds


if (UNIT_TESTING):
    print('si446x driver version: {}\n'.format(radio_version()))
    radio = radio_start_radio()
    config = radio_config_radio(radio)
    print('compiled config strings (wdds + local):\n')
    for s in config:
        print('{}'.format(insert_space(s)))


if (UNIT_TESTING):
    info = radio.read_silicon_info()
    for s in info:
        print(insert_space(s[0]), s[1])
    print(radio.get_gpio())


if (UNIT_TESTING):
    response = []
    request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
    request.cmd='PART_INFO'
    cmd = read_cmd_s.build(request)
    radio.spi.command(cmd, read_cmd_s.name)
    rsp = radio.spi.response(read_part_info_rsp_s.sizeof(),
                            read_part_info_rsp_s.name)
    if (rsp):
        response.append((rsp, read_part_info_rsp_s.parse(rsp)))
    request.cmd='FUNC_INFO'
    cmd = read_cmd_s.build(request)
    radio.spi.command(cmd, read_cmd_s.name)
    rsp = radio.spi.response(read_func_info_rsp_s.sizeof(),
                            read_func_info_rsp_s.name)
    if (rsp):
        response.append((rsp,read_func_info_rsp_s.parse(rsp)))
    print(response)


if (UNIT_TESTING):
    radio_show_config(radio.dump_radio())


if (UNIT_TESTING):
    for p_n in ['FRR_CTL', 'PA']:
        p_id = radio_config_group_ids.build(p_n)
        p_g = radio_config_groups[p_id]
        p_da = radio_get_group(radio, p_n)
        p_di = p_g.build(p_da)
        print('{} {}[{}]: ({}) {}'.format(p_n, p_g, hexlify(p_id), p_g.sizeof(), insert_space(p_di)))
        print(radio_display_structs[p_g](p_g, p_di))
        print(p_da)
        print()


if (UNIT_TESTING):
    s_name = 'pa_group_s'
    my_struct = eval(s_name)
    st = my_struct.parse('\x00' * my_struct.sizeof())
    data = my_struct.build(st)
    print('{}: {}'.format(s_name, radio_display_structs[my_struct](my_struct, data)))


if (UNIT_TESTING):
    pa_g = radio_get_group(radio, 'PA')
    pa_s = radio_config_groups[radio_config_group_ids.build('PA')]
    ps = pa_s.build(pa_g)
    print('{}: {}'.format(pa_s, insert_space(ps)))
    print(pa_g)
    print(radio_display_structs[pa_s](pa_s, ps))


if (UNIT_TESTING):
    print('\n programmed config strings:')
    for s in config:
        print(insert_space(s))
    print('\n const config strings:')
    for t in radio_get_raw_config():
        print(insert_space(t))
    assert(s==t)


if (UNIT_TESTING):
    g_name='FRR_CTL'
    g = radio_get_group(radio, g_name)
    print('{}: {}'.format(radio_config_groups[radio_config_group_ids.build(g_name)],
                          insert_space(radio_config_groups[radio_config_group_ids.build(g_name)].build(g))))
    print(g)


if (UNIT_TESTING):
    radio.set_power(10)
    g_name = 'PA'
    g = radio_get_group(radio, g_name)
    p = radio_config_groups[radio_config_group_ids.build(g_name)].build(g)
    print(radio_format_group('PA', p))
    radio.set_power(32)
    g = radio_get_group(radio, g_name)
    p = radio_config_groups[radio_config_group_ids.build(g_name)].build(g)
    print(radio_format_group('PA', p))


if (UNIT_TESTING):
    print(radio_get_group(radio, 'PA'))

if (UNIT_TESTING):
    """
    note that errors occur above threshold of 40. This implies interrupt latency is not satisfied.
    In runtime environment, use a value in range of 10 to 30. 10 could potentially cause more
    interrupts, but tolerates longer latency.
    """
    step = 1
    bb = bytearray(256)
    for i in range(len(bb)):
        bb[i] = i
    radio.trace._enable()
    ss = bytearray('\x10\x10')
    for thresh in range(20,21,step):
        print('thresh: {}'.format(thresh))
        ss[0] = thresh
        ss[1] = thresh
        radio.set_property('PKT', 0x0b, ss) # tx/rx threshold
        for i in range(80,81,step):
            bb[0] = i + 20
            pl = radio_send_msg(radio, bb[:i], 6)
            print('{} {}'.format(i, ''.join(map(str, pl))))
            print(hexlify(bb[:i]))
            if (pl[-1] == 'e'):
                print('ERROR {} {}'.format(i, ''.join(map(str, pl))))
            sleep(1)
    print('\ndone')

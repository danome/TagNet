# coding: utf-8

# Si446x Device Direct Access Layer Access
#
# This notebook explores the Si446xRadio class, which handles the direct access to operating system provided SPI bus and GPIO interface pins that connect to the Si446x device. This provides the command and control interface provided by the device.

from __future__ import print_function
import RPi.GPIO as GPIO
import sys
import os
sys.path.append("../si446x") # go to parent dir
sys.path.append("../") # go to parent dir
from si446x import *

UNIT_TESTING = False

import types
from binascii import hexlify

# zzz debugging
# os.path.abspath(os.getcwd())
# for p in sys.path:
#     print(p)


# ## Get Device Driver Version

from si446x import __version__

def si446x_device_version():
    return __version__


radio = None

# ##  Start up Radio

def si446x_device_start_radio():
    global radio
    print('Si446x Radio Device Driver Version: {}'.format(si446x_device_version()))
    radio=Si446xRadio(0)
    radio.unshutdown()
    radio.power_up()
    return radio


# ## Configure Radio

def si446x_device_config_radio(radio):
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


# ## Get Radio Property Group

def si446x_device_get_group(radio, g_n):
    g_s = radio_config_groups[radio_config_group_ids.build(g_n)]
    return g_s.parse(si446x_device_get_property(radio, g_n, 0, g_s.sizeof()))


# ## Get Radio Property

def si446x_device_get_property(radio, g_n, start, limit):
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


# ## Format Radio Property Group

def si446x_device_format_group(gn, data):
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


# ##  Show Radio Configuration

def si446x_device_show_config(config):
    total = 0
    for k, v in config.iteritems():
        total += len(v)
        s = radio_config_groups[k]
        p = radio_display_structs[s]
        print('\n{}: {}\n{}'.format(s.name, s.sizeof(), insert_space(v)))
        print(p(s,v))
    print('\n=== total: {}'.format(total))


# ## Get Compiled Radio Configuration

from si446x import get_config_wds, get_config_device

def si446x_device_get_raw_config():
    rl = []
    for l in [get_config_wds, get_config_device]:
        x = 0
        while (True):
            s = l(x)
            if (not s): break
            rl.append(s)
            x += len(s) + 1
    return rl


# ## Get Radio Interrupt Information

def int_status(clr_flags=None, show=False):
    clr_flags = clr_flags if (clr_flags) else \
                clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    clr_flags.ph_pend.STATE_CHANGE = False    # always clear this interrupt
    p_g = radio.get_clear_interrupts(clr_flags)
    if (show is True):
        s_name =  'int_status_rsp_s'
        p_s = eval(s_name)
        p_d = p_s.build(p_g)
#        print('{}: {}'.format(s_name, hexlify(p_d)))
        print(radio_display_structs[p_s](p_s, p_d))
    return p_g


def old_int_status(clr_flags=None, show=False):
    clr_flags = clr_flags if (clr_flags) else clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    clr_flags.ph_pend.STATE_CHANGE = False
    p_g = radio.get_clear_interrupts(clr_flags)
    if (show is True):
        s_name =  'int_status_rsp_s'
        p_s = eval(s_name)
        p_d = p_s.build(p_g)
#        print('{}: {}'.format(s_name, hexlify(p_d)))
        print(radio_display_structs[p_s](p_s, p_d))
    return p_g


def show_int_rsp(pend_flags):
    s_name =  'int_status_rsp_s'
    p_s = eval(s_name)
    clr_flags = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    clr_flags.ph_pend.STATE_CHANGE = False
    p_g = radio.get_clear_interrupts(clr_flags)
    p_d = p_s.build(p_g)
#    print('{}: {}'.format(s_name, hexlify(p_d)))
    print(radio_display_structs[p_s](p_s, p_d))


# ## Send a complete message

from si446x  import clr_pend_int_s

clr_all_flags = clr_pend_int_s.parse('\00' * clr_pend_int_s.sizeof())
clr_no_flags  = clr_pend_int_s.parse('\ff' * clr_pend_int_s.sizeof())

MAX_FIFO_SIZE = 64


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


def si446x_device_send_msg(radio, msg, pwr):
    progress = []
    show_flag = False

    msg_chunk = msg_chunk_generator(radio, msg)

    int_status(clr_all_flags, show_flag)
    radio.set_power(pwr)

    __, tx = radio.fifo_info(rx_flush=True, tx_flush=True)
    if (tx != MAX_FIFO_SIZE): print('tx fifo bad: {}'.format(tx))

    chunk, p = next(msg_chunk)
    progress.extend(p)
    radio.write_tx_fifo(chunk)
    radio.start_tx(len(msg))

#    return progress

    cflags = clr_no_flags
    while (True):
        status = int_status(cflags, show_flag)
        cflags = clr_no_flags
        no_action = True
        if (status.ph_pend.TX_FIFO_ALMOST_EMPTY):
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
    status = int_status(clr_all_flags)

    return progress


# ## Receive a complete message

from datetime import datetime, timedelta

def drain_rx_fifo(p):
    rx_len, __ = radio.fifo_info()
    if (rx_len > MAX_FIFO_SIZE):
        rx_len = MAX_FIFO_SIZE
        p.append('?')
    p.append(rx_len)
#    rx = 0  # force the fifo read to fail to verify overrun error
    if (rx_len): return bytearray(radio.read_rx_fifo(rx_len))
    else:    return ''

def si446x_device_receive_msg(radio, max_recv, wait):
    start = datetime.now()
    delta= timedelta(seconds=wait)
    end = start + delta
    msg = bytearray()
    progress = []
    show = False
    rssi = -1
    int_status(clr_all_flags)
    radio.fifo_info(rx_flush=True, tx_flush=True)
    radio.start_rx(0)
    status = int_status(clr_no_flags)
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
            msg += drain_rx_fifo(progress)
            progress.append('.')
            rx, tx = radio.fifo_info()
            progress.append(rx)
        if (status.ph_pend.PACKET_RX):
            rssi = radio.fast_latched_rssi()
            cflags.ph_pend.PACKET_RX = False
            progress.append('f')
            msg += drain_rx_fifo(progress)
            progress.append('.')
            rx, tx = radio.fifo_info()
            progress.append(rx)
            progress.append(':')
            progress.append(len(msg))
            break
        if (status.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR):
            cflags.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR = False
            break
        status = int_status(cflags, show)
    status = int_status()
    pkt_len = radio.get_packet_info()
    if (datetime.now() > end):
        progress.extend(['to','e'])
    elif ((pkt_len + 1) != len(msg)):
        progress.extend(['e', pkt_len + 1,',',len(msg),'e'])
    return (msg, rssi, progress)


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
    print('si446x driver version: {}\n'.format(si446x_device_version()))
    radio = si446x_device_start_radio()
    config = si446x_device_config_radio(radio)
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
    si446x_device_show_config(radio.dump_radio())


if (UNIT_TESTING):
    for p_n in ['FRR_CTL', 'PA']:
        p_id = radio_config_group_ids.build(p_n)
        p_g = radio_config_groups[p_id]
        p_da = si446x_device_get_group(radio, p_n)
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
    pa_g = si446x_device_get_group(radio, 'PA')
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
    for t in si446x_device_get_raw_config():
        print(insert_space(t))
    assert(s==t)


if (UNIT_TESTING):
    g_name='FRR_CTL'
    g = si446x_device_get_group(radio, g_name)
    print('{}: {}'.format(radio_config_groups[radio_config_group_ids.build(g_name)],
                          insert_space(radio_config_groups[radio_config_group_ids.build(g_name)].build(g))))
    print(g)


if (UNIT_TESTING):
    radio.set_power(10)
    g_name = 'PA'
    g = si446x_device_get_group(radio, g_name)
    p = radio_config_groups[radio_config_group_ids.build(g_name)].build(g)
    print(si446x_device_format_group('PA', p))
    radio.set_power(32)
    g = si446x_device_get_group(radio, g_name)
    p = radio_config_groups[radio_config_group_ids.build(g_name)].build(g)
    print(si446x_device_format_group('PA', p))


if (UNIT_TESTING):
    print(si446x_device_get_group(radio, 'PA'))


from time import sleep


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
            pl = si446x_device_send_msg(radio, bb[:i], 6)
            print('{} {}'.format(i, ''.join(map(str, pl))))
            print(hexlify(bb[:i]))
            if (pl[-1] == 'e'):
                print('ERROR {} {}'.format(i, ''.join(map(str, pl))))
            sleep(1)
    print('\ndone')

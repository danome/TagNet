
import spidev

# to_send = [0x01, 0x02, 0x03]
# spi.xfer(to_send)
# Perform an SPI transaction with chip-select should be held active between blocks.
# xfer2(to_send[, speed_hz, delay_usec, bits_per_word])

def BytesToHex(Bytes):
    return ''.join(["0x%02X " % x for x in Bytes]).strip()
#end def

import si446xdef
#from si446xradio import Si446xRadio

from time import sleep

##########################################################################
#
# utility routines
#
def start_timer(timeout):
    sleep(float(timeout/1000))
    pass

def fail(s):
    print("FAIL: ", s)
    while (0):
        x = 1
    pass

def _trace(where, ev):
    #print('trace', ev, where)
    pass


##########################################################################
#
# FsmActionHandlers - The method handlers for actions in the Finite State Machine
#
class FsmActionHandlers(object):
    def __init__(self, radio):
        self.radio = radio
        self.ioc = {
            'unshuts': 0,
        }
        self.rx = {
            'packets': 0,
            'errors': 0,
            'rssi': 0,
            'offset' :0,
            'timeouts': 0,
            'sync_errors': 0,
            'crc_errors': 0,
            'buffer': [],
        }
        self.tx = {
            'packets': 0,
            'errors': 0,
            'offset' :0,
            'timeouts': 0,
            'buffer': [],
        }

    def output_A_CLEAR_SYNC(self, ev):
        _trace("clear sync", ev)
        clear_sync(self, ev)

    def output_A_CONFIG(self, ev):
        _trace("config", ev)
        config(self, ev)

    def output_A_NOP (self, ev):
        _trace("nop", ev)
        no_op(self, ev)

    def output_A_PWR_DN(self, ev):
        _trace("power down", ev)
        pwr_dn(self, ev)

    def output_A_PWR_UP(self, ev):
        _trace("power up", ev)
        pwr_up(self, ev)

    def output_A_READY (self, ev):
        _trace("ready", ev)
        ready(self, ev)

    def output_A_RX_CMP(self, ev):
        _trace("rx complete", ev)
        rx_cmp(self, ev)

    def output_A_RX_CNT_CRC(self, ev):
        _trace("rx count crc error", ev)
        rx_cnt_crc(self, ev)

    def output_A_RX_DRAIN_FF(self, ev):
        _trace("drain rx fifo", ev)
        rx_drain_ff(self, ev)
        
    def output_A_RX_START(self, ev):
        _trace("rx start", ev)
        rx_start(self, ev)
        
    def output_A_RX_TIMEOUT(self, ev):
        _trace("rx timeout", ev)
        rx_timeout(self, ev)
        
    def output_A_STANDBY(self, ev):
        _trace("standby", ev)
        standby(self, ev)
        
    def output_A_TX_CMP(self, ev):
        _trace("tx complete", ev)
        tx_cmp(self, ev)
        
    def output_A_TX_FILL_FF(self, ev):
        _trace("tx fill fifo", ev)
        tx_fill_ff(self, ev)
        
    def output_A_TX_START(self, ev):
        _trace("tx start", ev)
        tx_start(self, ev)
        
    def output_A_TX_TIMEOUT(self, ev):
        _trace("tx timeout", ev)
        tx_timeout(self, ev)
        
    def output_A_UNSHUT(self, ev):
        _trace("unshutdown", ev)
        unshut(self, ev)
#end class


##########################################################################
#
# Actions that operate on the radio
#

#
def clear_sync(me, ev):
    me.radio.fifo_info(rx_flush=True)
    me.rx['sync_errors'] += 1
    rx_on(me, ev)

#
def config(me, ev):
    me.radio.config_frr()  # assign sources to the fast registers
    list_of_lists = me.radio.get_config_lists()
    for l in list_of_lists:
        x = 0
        while (True):
            s = l(x)
            if (not s): break
            me.radio.send_config(s)
            x += len(s) + 1
    # special override - enable specific interrupt sources
    me.radio.set_property('INT_CTL', 4, 0, '\x03\x3b\x23\x00')
    me.radio.dump_radio()

#
def no_op(me, ev):
    pass

#
def pwr_dn(me, ev):
    #zzz stop_alarm
    me.radio.disable_interrupt()
    me.radio.shutdown()
#
def pwr_up(me, ev):
    # check ctsn and fail if not true (negative logic)
    if (not me.radio.get_cts()):  fail('power up failed to get cts acknowledgement')
    start_timer(si446xdef.POWER_UP_WAIT_TIME)
    me.radio.power_up()
#
def ready(me, ev):
    me.radio.set_channel(me.radio.get_channel())
    me.radio.clear_interrupts()
    me.radio.dump_radio()
    me.radio.dump_display()
    me.radio.enable_interrupts()
    rx_on(me, ev)
#
def rx_cmp(me, ev):
    #zzz stop alarm
    rx_drain_ff(me, ev)
    pkt_len = me.radio.get_packet_info() + 1 # add 1 for length field
    if (me.rx['offset'] != pkt_len):
        print('rx_cmp: error in packet length', me.rx['offset'], pkt_len)
    #zzz send receive event notification
    #print('rx_cmp: ', pkt_len, me.rx['offset'], me.rx['buffer'].encode('hex'))
    me.rx['packets'] += 1
    me.radio.change_state('READY', 1)
    print('#')
    rx_on(me, ev)
#
def rx_cnt_crc(me, ev):
    #zzz stop_alarm
    me.rx['crc_errors'] += 1
    me.radio.fifo_info(rx_flush=True)
    me.radio.change_state('SLEEP', 100) # ms *debugging
    me.radio.clear_interrupts()
    rx_on(me, ev)
#
def rx_drain_ff(me, ev):
    for i in range(10):
        rx_len, tx_free = me.radio.fifo_info()
        if (rx_len):
            me.rx['buffer'] += me.radio.read_rx_fifo(rx_len)
            me.rx['offset'] += rx_len
        else:
            if (ord(me.radio.fast_ph_pend()) & 0x10):
                break
            sleep(0)
#
def rx_on(me, ev):
    #zzz stop alarm
    me.radio.fifo_info(rx_flush=True, tx_flush=True)
    me.radio.clear_interrupts()
    me.radio.start_rx(0)
#
def rx_start(me, ev):
    #zzz start alarm
    me.rx['rssi'] = me.radio.fast_latched_rssi()
    #zzz set packet rssi field
    me.rx['buffer'] = []
    me.rx['offset'] = 0
#
def rx_timeout(me, ev):
    me.rx['timeouts'] += 1
    me.radio.start_rx(0)
#
def standby(me, ev):
    #zzz stop_alarm
    me.radio.change_state('SLEEP', 100) # ms
#
def tx_cmp(me, ev):
    #zzz stop_alarm
    me.tx['packets'] += 1
    rx_len, tx_free = me.radio.fifo_info()
    if (tx_free != TX_FIFO_MAX):
        print('tx_cmp: fifo not empty, missed data')
    #zzz report completion
    rx_on(me, ev)
#
def tx_fill_ff(me, ev):
    pkt_len = len(me.tx['buffer'])
    start_offset = me.tx['offset']
    remaining_len = pkt_len - start_offset
    if (remaining_len > 0):
        rx_len, tx_free = me.radio.fifo_info(tx_flush=True)
        if (tx_free == TX_FIFO_MAX):
            print('tx_fill_ff: fifo empty, too late')
        me.tx['offset'] += remaining_len if (remaining_len < tx_free) else tx_free
        segment = me.tx['buffer'][start_offset:me.tx['offset']]
        me.radio.write_tx_fifo(segment)
#
def tx_start(me, ev):
    pkt_len = len(me.tx['buffer'])
    rx_len, tx_free = me.radio.fifo_info(tx_flush=True)
    if (tx_free != TX_FIFO_MAX):
        print('tx_start: should be fifo empty')
    me.tx['offset'] = pkt_len if (pkt_len < tx_free) else tx_free
    segment = radio['buffer'][0:me.tx['offset']]
    me.radio.write_tx_fifo(segment)
    start_tx(pkt_len)
    #zzz start alarm
#
def tx_timeout(me, ev):
    me.tx['timeouts'] += 1
    rx_on(me, ev)
#
def unshut(me, ev):
    start_timer(si446xdef.POWER_ON_WAIT_TIME)
    me.radio.unshutdown()
    me.ioc['unshuts'] + 1
    #zzz clear flags, buffers, statistics
    return

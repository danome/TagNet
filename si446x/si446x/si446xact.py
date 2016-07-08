
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
def start_timer(actions, delay):
    actions.timer = actions.dbus.start_timer(delay)

def stop_timer(actions):
    if (not actions.timer):
        return
    try:
        actions.timer.cancel()
    except twisted.internet.error.AlreadyCalled:
        pass
    except twisted.internet.error.AlreadyCancelled:
        pass
    actions.timer = None

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
class Si446xFsmActionHandlers(object):
    
    def __init__(self, radio, dbus):
        self.dbus = dbus
        self.radio = radio
        self.timer = None
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
            'power': 0,
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
def clear_sync(actions, ev):
    actions.radio.fifo_info(rx_flush=True)
    actions.rx['sync_errors'] += 1
    rx_on(actions, ev)
#
def config(actions, ev):
    actions.radio.config_frr()  # assign sources to the fast registers
    list_of_lists = actions.radio.get_config_lists()
    for l in list_of_lists:
        x = 0
        while (True):
            s = l(x)
            if (not s): break
            actions.radio.send_config(s)
            x += len(s) + 1
    ### local instance overrides
    # enable specific interrupt sources
    actions.radio.set_property('INT_CTL', 0, '\x03\x3b\x23\x00')
    # lower rx fifo threshold
    actions.radio.set_property('PKT', 0x0c, '\x10')
    # remember all of the current radio settings
    actions.radio.dump_radio()
#
def no_op(actions, ev):
    pass
#
def pwr_dn(actions, ev):
    stop_timer(actions)
    actions.radio.disable_interrupt()
    actions.radio.shutdown()
#
def pwr_up(actions, ev):
    # check ctsn and fail if not true (negative logic)
    if (not actions.radio.get_cts()):
        fail('power up failed to get cts acknowledgement')
    start_timer(actions, si446xdef.POWER_UP_WAIT_TIME)
    actions.radio.power_up()
#
def ready(actions, ev):
    actions.radio.set_channel(actions.radio.get_channel())
    actions.radio.clear_interrupts()
    actions.radio.dump_radio()
    actions.radio.dump_display()
    actions.radio.enable_interrupts()
    rx_on(actions, ev)
#
def rx_cmp(actions, ev):
    stop_timer(actions)
    rx_drain_ff(actions, ev)
    pkt_len = actions.radio.get_packet_info() + 1 # add 1 for length field
    if (actions.rx['offset'] != pkt_len):
        print(actions.radio.fifo_info())
        print('e', actions.rx['offset'], pkt_len)
    #zzz send receive event notification
    #print('rx_cmp: ', pkt_len, actions.rx['offset'], actions.rx['buffer'].encode('hex'))
    actions.rx['packets'] += 1
    #actions.radio.change_state('READY', 1)
    print('#')
    actions.dbus.signal_receive()
    rx_on(actions, ev)
#
def rx_cnt_crc(actions, ev):
    stop_timer(actions)
    actions.rx['crc_errors'] += 1
    actions.radio.fifo_info(rx_flush=True)
    actions.radio.change_state('SLEEP', 100) # ms *debugging
    actions.radio.clear_interrupts()
    rx_on(actions, ev)
#
def rx_drain_ff(actions, ev):
    for i in range(1):
        rx_len, tx_free = actions.radio.fifo_info()
        if (rx_len):
            print(rx_len)
            actions.rx['buffer'] += actions.radio.read_rx_fifo(rx_len)
            actions.rx['offset'] += rx_len
        else:
            if (ord(actions.radio.fast_ph_pend()) & 0x10):
                break
#            sleep(0)
#
def rx_on(actions, ev):
    stop_timer(actions)
    actions.radio.fifo_info(rx_flush=True, tx_flush=True)
    actions.radio.clear_interrupts()
    actions.radio.start_rx(0)
#
def rx_start(actions, ev):
    start_timer(actions, si446xdef.RX_WAIT_TIME)
    actions.rx['rssi'] = actions.radio.fast_latched_rssi()
    #zzz set packet rssi field
    actions.rx['buffer'] = []
    actions.rx['offset'] = 0
#
def rx_timeout(actions, ev):
    actions.rx['timeouts'] += 1
    actions.radio.start_rx(0)
#
def standby(actions, ev):
    stop_timer(actions)
    actions.radio.change_state('SLEEP', 100) # ms
#
def tx_cmp(actions, ev):
    stop_timer(actions)
    actions.tx['packets'] += 1
    rx_len, tx_free = actions.radio.fifo_info()
    if (tx_free != TX_FIFO_MAX):
        print('tx_cmp: fifo not empty, missed data')
    actions.dbus.signal_send_cmp('ok')
    rx_on(actions, ev)
#
def tx_fill_ff(actions, ev):
    pkt_len = len(actions.tx['buffer'])
    start_offset = actions.tx['offset']
    remaining_len = pkt_len - start_offset
    if (remaining_len > 0):
        rx_len, tx_free = actions.radio.fifo_info(tx_flush=True)
        if (tx_free == TX_FIFO_MAX):
            print('tx_fill_ff: fifo empty, too late')
        actions.tx['offset'] += remaining_len if (remaining_len < tx_free) else tx_free
        segment = actions.tx['buffer'][start_offset:actions.tx['offset']]
        actions.radio.write_tx_fifo(segment)
#
def tx_start(actions, ev):
    pkt_len = len(actions.tx['buffer'])
    rx_len, tx_free = actions.radio.fifo_info(tx_flush=True)
    if (tx_free != TX_FIFO_MAX):
        print('tx_start: should be fifo empty')
    actions.tx['offset'] = pkt_len if (pkt_len < tx_free) else tx_free
    segment = radio['buffer'][0:actions.tx['offset']]
    actions.radio.write_tx_fifo(segment)
    start_tx(pkt_len)
    start_timer(actions, si446xdef.TX_WAIT_TIME)

#
def tx_timeout(actions, ev):
    actions.tx['timeouts'] += 1
    actions.dbus.signal_send_cmp('timeout') # no retries
    rx_on(actions, ev)
#
def unshut(actions, ev):
    start_timer(actions, si446xdef.POWER_ON_WAIT_TIME)
    actions.radio.unshutdown()
    actions.ioc['unshuts'] + 1
    #zzz clear flags, buffers, statistics
    return

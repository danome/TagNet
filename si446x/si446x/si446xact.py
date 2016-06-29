
import spidev
# to_send = [0x01, 0x02, 0x03]
# spi.xfer(to_send)
# Perform an SPI transaction with chip-select should be held active between blocks.
# xfer2(to_send[, speed_hz, delay_usec, bits_per_word])

def BytesToHex(Bytes):
    return ''.join(["0x%02X " % x for x in Bytes]).strip()
#end def

import si446xdef
from si446xradio import Si446xRadio

from time import sleep
#from array import array

POWER_ON_WAIT_TIME     = 500          # milliseconds
POWER_UP_WAIT_TIME     = 100          # milliseconds
TX_FIFO_MAX            = 64
RX_EMPTY               = 0

def start_timer(timeout):
    sleep(1)
    pass

def fail(s):
    print("FAIL: ", s)
    while (0):
        x = 1
    pass

class Si446xActionProcs(object):
    def __init__(self, dev_num):
        self.radio = Si446xRadio(dev_num)
        self.ioc = {
            'unshuts': 0,
        }
        self.rx = {
            'packets': 0,
            'errors': 0,
            'rssi': 0,
            'offset' :0,
            'timeouts': 0,
            'buffer': '',
        }
        self.tx = {
            'packets': 0,
            'errors': 0,
            'offset' :0,
            'timeouts': 0,
            'buffer': '',
        }
    
    def clear_sync(self, ev):
        self.rx['sync_errors'] += 1
        self.radio.fifo_info(rx_flush=True)
        self.rx_on(ev)

    def config(self, ev):
        self.radio.read_silicon_info()
        self.radio.read_cmd_buff()
        list_of_lists = self.radio.get_config_lists()
        for l in list_of_lists:
            x = 0
            while (True):
                s = l(x)
                if (not s): break
                self.radio.send_config(s)
                x += len(s) + 1
        #zzz clear flags, buffers, statistics

    def no_op(self, ev):
        self.radio.read_silicon_info()
        self.radio.read_cmd_buff()
    
    def pwr_dn(self, ev):
        #zzz stop_alarm
        self.radio.disable_interrupt()
        self.radio.shutdown()
    
    def pwr_up(self, ev):
        # check ctsn and fail if not true (negative logic)
        if (not self.radio.get_cts()):  fail('power up failed to get cts acknowledgement')
        start_timer(POWER_UP_WAIT_TIME)
        self.radio.power_up()

    def ready(self, ev):
        self.radio.set_channel(self.radio.get_channel())
        self.radio.clear_interrupts(255,255,255)
        self.radio.enble_interrupt()
        self.radio.dump_radio()
        self.rx_on(ev)

    def rx_cmp(self, ev):
        pkt_len = self.radio.get_packet_info() + 1 # add 1 for length field
        rx_len, fifo_free = self.radio.fifo_info()
        self.rx['buffer'] += self.radio.read_rx_fifo(rx_len)
        self.rx['offset'] += rx_len
        if (self.rx['offset'] < pkt_len):
            print('rx_cmp: error in packet length')
        #zzz send receive event notification
        self.rx['packets'] += 1
        self.rx_on(ev)

    def rx_cnt_crc(self, ev):
        self.rx['crc_errors'] += 1
        self.radio.fifo_info(rx_flush=True)
        self.radio.change_state('SLEEP')
        self.clear_interrupts(255,255,255)
        #zzz stop_alarm
        self.rx_on(ev)

    def rx_drain_ff(self, ev):
        rx_len, tx_len = self.radio.fifo_info()
        self.rx['buffer'] += self.radio.read_rx_fifo(rx_len)
        self.rx['offset'] += rx_len
    
    def rx_on(self, ev):
        self.radio.fifo_info(rx_flush=True, tx_flush=True)
        self.radio.clear_interrupts(255,255,255)
        self.radio.start_rx(0)
    
    def rx_start(self, ev):
        self.rx['rssi'] = self.radio.fast_latched_rssi()
        #zzz set packet rssi field
        #zzz start alarm
        self.rx[buffer] = ''
        self.rx['offset'] = 0

    def rx_timeout(self, ev):
        self.rx['timeouts'] += 1
        self.radio.start_rx(0)
    
    def standby(self, ev):
        #zzz stop_alarm
        self.radio.change_state('SLEEP')
        pass
    
    def tx_cmp(self, ev):
        #zzz stop_alarm
        self.tx['packets'] += 1
        rx_len, tx_free = self.radio.fifo_info()
        #zzz check for errors
        self.radio.start_rx(0)
    
    def tx_fill_ff(self, ev):
        pkt_len = len(self.tx['buffer'])
        start_offset = self.tx['offset']
        remaining_len = pkt_len - start_offset
        if (remaining_len > 0):
            rx_len, tx_free = self.radio.fifo_info(tx_flush=True)
            if (tx_free == TX_FIFO_MAX):
                print('tx_fill_ff: fifo empty, too late')
            self.tx['offset'] += remaining_len if (remaining_len < tx_free) else tx_free
            segment = self.radio['buffer'][start_offset:self.tx['offset']]
            self.radio.write_tx_fifo(segment)
    
    def tx_start(self, ev):
        pkt_len = len(self.tx['buffer'])
        rx_len, tx_free = self.radio.fifo_info(tx_flush=True)
        if (tx_free != TX_FIFO_MAX):
            print('tx_start: fifo not empty')
        self.tx['offset'] = pkt_len if (pkt_len < tx_free) else tx_free
        segment = self.radio['buffer'][0:self.tx['offset']]
        self.radio.write_tx_fifo(segment)
        self.start_tx(pkt_len)
        #zzz start alarm

    def tx_timeout(self, ev):
        self.tx['timeouts'] += 1
        self.radio.start_rx(0)
    
    def unshut(self, ev):
        start_timer(POWER_ON_WAIT_TIME)
        self.radio.unshutdown()
        #zzz clear flags, buffers, statistics
        return

#end class





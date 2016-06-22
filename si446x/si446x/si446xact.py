
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

POWER_ON_WAIT_TIME = 500          # milliseconds
POWER_UP_WAIT_TIME = 100          # milliseconds


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
        pass
    
    def unshut(self):
        start_timer(POWER_ON_WAIT_TIME)
        self.radio.unshutdown()
        # clear flags, buffers, statistics
        return

    def pwr_up(self):
        # check ctsn and fail if not true (negative logic)
        if (not self.radio.get_cts()):  fail('power up failed to get cts acknowledgement')
        start_timer(POWER_UP_WAIT_TIME)
        self.radio.power_up()
        return

    def config(self):
        self.radio.read_silicon_info()
        self.radio.read_cmd_buff()
        # clear flags, buffers, statistics
        return
    
#end class





from __future__ import print_function   # python3 print function
from builtins import *

from time import sleep, localtime
import binascii

from construct import *

import spidev

try:
    import RPi.GPIO as GPIO
    gpio = True
except RuntimeError as e:
    gpio = False
    print(e)

from si446xdef import *
from si446xcfg import get_config_wds, get_config_local
import si446xtrace

__all__ = ['SpiInterface', 'Si446xRadio', 'si446xradio_test']

"""
This Module handles access to the Si446x Radio hardware interface.

The interface consists of:
- Serial Peripherial Interface  =  four-wire interface (DI,DO,CLK,CS)
- General Purpose IO            =  input pins (CTS, NIRQ, SDN)

The SpiInterface class provides the methods for accessing the radio SPI.
This includes sending commands, receiving responses, writing the transmit
fifo, reading the receive fifo, and reading the fast response registers.
All radio SPI IO accesses are handled by this class and recorded in a
circular trace buffer for later analysis.

The GPIO is accessed using the Raspberry Pi Python RPi.GPIO module.

The Si446xRadio class provides a set of methods for operating on the radio,
such as starting, stopping, configuring, interrupts, and checking status.
In most cases, these methods accept/return the dictionary version of any
radio structures used in the operation (see si446xdef.py). One exception,
for example, is get_property(). Significant events are recorded in the
trace buffer for later analysis.
"""

def _get_cts():
    """
    Read the current value of the radio CTS GPIO pin

    Internal use only.
    """
    if (gpio):
        return (GPIO.input(GPIO_CTS))
    else:
        return False

def _get_cts_wait(t):
    """
    Wait for the value of the radio CTS GPIO pin to go high (True)

    Internal use only.
    """
    if (gpio):
        for i in range(t+1):
            r = _get_cts()
            if (r or (t == 0)):  return r
            sleep(.001)
    return False


class SpiInterface:
    """
    Class to access the Si446x over SPI interface

    Basic access to the Si446x device uses the SPI interface. The methods
    of this class contain the semantics for accessing the device bus
    registers. The Si446x device contains an internal processor, much
    of the communication involves command and response exchanges
    through a 16-byte shared memory buffer. Data is transferred through
    direct access to the transmit and receive fifos. Additional,
    a set of four special registers can be directly accessed through
    bus registers. Otherwise, all configuration and status is exchanged
    through messages.

    Note: SPI device driver controls chip select and performs an SPI
          transaction with chip-select held active throughout the transfer.
          For example:
          to_send = [0x01, 0x02, 0x03]
          xfer2(to_send[, speed_hz, delay_usec, bits_per_word])
    """
    def __init__(self, device, trace=None):
        """
        Initialize the SPI interface

        Establish connection to device provided by spidev and RPi and
        set speed
        """
        try:
            self.trace = trace if (trace) else si446xtrace.Trace(100)
            self.device = device
            self.spi = spidev.SpiDev()
            self.spi.open(0, device)  # port=0, device(CS)=device_num
            #self.spi.max_speed_hz=600000
            self.trace.add('RADIO_CHIP',
                           'spi max speed: {}'.format(self.spi.max_speed_hz),
                           level=2)
        except IOError as e:
            self.trace.add('RADIO_INIT_ERROR', e, level=2)

    def command(self, msg, form):
        """
        Send command message to the device

        Wait for CTS and then SPI write the msg
        """
        _get_cts_wait(100)
        if (not _get_cts()):
            self.trace.add('RADIO_CTS_ERROR', 'no cts [1]', level=2)
        try:
            self.form = form
            self.trace.add('RADIO_CMD', bytearray(msg), s_name=form, level=2)
            self.spi.xfer2(list(bytearray(msg)))
        except IOError as e:
            self.trace.add('RADIO_CMD_ERROR', e, level=2)

    def response(self, rlen, form):
        """
        Get msg response for previous command

        Wait for CTS and then SPI read back the response buffer.
        """
        _get_cts_wait(100)
        rsp = bytearray()
        if (not _get_cts()):
            self.trace.add('RADIO_RSP_ERROR', 'no cts [2]', level=2)
        try:
            r = self.spi.xfer2([0x44] + rlen * [0])
            rsp = bytearray(r) if (r[0]) else bytearray(r[1:]) # zzz funky
            form = form if (form) else self.form
            self.trace.add('RADIO_RSP', rsp, s_name=form, level=2)
        except IOError as e:
            self.trace.add('RADIO_RSP_ERROR', e, level=2)
        return rsp

    def read_fifo(self, rlen):
        """
        SPI read data from the Receive FIFO
        """
        if (rlen > RX_FIFO_MAX):
            self.trace.add('RADIO_RX_TOO_LONG', 'len: {}'.format(rlen), level=2)
        r = self.spi.xfer2([0x77] + rlen * [0])
        self.trace.add('RADIO_RX_FIFO', len(r)-1, level=2)
        return bytearray(r[1:])

    def write_fifo(self, buf):
        """
        SPI write data to the Transmit FIFO
        """
        if (len(buf) > TX_FIFO_MAX):
            self.trace.add('RADIO_TX_TOO_LONG', 'len: {}'.format(len(buf)), level=2)
        self.trace.add('RADIO_TX_FIFO', 'len: {}'.format(len(buf)), level=2)
        r = self.spi.xfer2([0x66] + list(buf))

    def read_frr(self, off, len):
        """
        SPI read the fast read registers
        """
        index = [0,1,3,7]
        if (len > 4):
            self.trace.add('RADIO_FRR_TOO_LONG', 'len: {}, off: {}'.format(len,off), level=2)
        r = self.spi.xfer2([0x50 + index[off]] + len * [0])
        rsp = bytearray(r[1:len+1])
        self.trace.add('RADIO_FRR', rsp, s_name=fast_frr_s.name, level=2)
        return rsp
#end class


class Si446xRadio(object):
    """
    Class for handling low level Radio device operations.

    This is the radio API for the SI446x ('63 specifically, but verified
    to operate with '68 as well -tbd)
    """
    def __init__(self, device=0, callback=None, trace=None):
        """
        Initialize Si446x Radio Device API

        RPi defines a single SPI interface with two chip selects. This
        allows for two devices (0 and 1) to be connected and separately
        accessed. A SpiInterface object is created for one of these devices.

        The callback function handles the RPi interrupt from the GPIO
        pin which should be wired to the radio interrupt pin. See
        """
        self.trace = trace if (trace) else si446xtrace.Trace(100)
        self.channel = 0
        self.callback = callback if (callback) else self._gpio_callback
        self.dump_strings = {}
        self.spi = SpiInterface(device, trace=self.trace)
    #end def

    def _gpio_callback(self, channel):
        self.trace.add('RADIO_ERROR', 'si446xradio: Edge detected on channel %s'%channel)

    def change_state(self, state,  wait=0):
        """
        change_state - force radio chip to change to specific state

        waits (ms) for acknowledgement that radio has processed the change.
        """
        request = change_state_cmd_s.parse('\x00' * change_state_cmd_s.sizeof())
        request.cmd = 'CHANGE_STATE'
        request.state = state
        cmd = change_state_cmd_s.build(request)
        self.spi.command(cmd, change_state_cmd_s.name)
        _get_cts_wait(wait)
    #end def

    def check_CCA(self):
        """
        Perform Clear Channel Assessment

        Return False if signal is detected (rssi above threshold).
        """
        rssi = self.fast_latched_rssi()
        return True if (rssi < si446x_cca_threshold) else False
    #end def

    def clear_interrupts(self, clr_flags=None):
        """
        Clear radio chip pending interrupts

        Default (nothing in clr_flags) then clear all interrupts by
        sending short command. Otherwise, send the flags to clear.
        (flag == 0 means clear pending interrupt (yes, 0))
        """
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='GET_INT_STATUS'
        cf = clr_pend_int_s.build(clr_flags) if (clr_flags) else ''
        cmd = read_cmd_s.build(request) + cf
        s_name = get_clear_int_cmd_s.name if (cf) else read_cmd_s.name
        self.spi.command(cmd, s_name)
        self.trace.add('RADIO_PEND', cmd, s_name=s_name, level=2)
    #end def

    def config_frr(self,
                   a_mode='CURRENT_STATE',
                   b_mode='INT_PH_PEND',
                   c_mode='INT_MODEM_PEND',
                   d_mode='LATCHED_RSSI'):
        """
        Configure the Fast Response Registers (FRR) to the specific Driver usage

        FRR should be set explicitly right after POWER_UP to the following:
        A: CURRENT_STATE   - current state of the radio
        B: PH_PEND         - packet handler pending interrupts
        C: MODEM_PEND      - modem pending interrupts
        D: LATCHED_RSSI    - current latched RSSI valu

        We use LR (Latched_RSSI) when receiving a packet.  The RSSI value is
        attached to the last RX packet.  The Latched_RSSI value may, depending
        on configuration, be associated with some number of bit times once RX
        is enabled or when SYNC is detected.
        """
        request = config_frr_cmd_s.parse('\x00' * config_frr_cmd_s.sizeof())
        request.cmd='SET_PROPERTY'
        request.group='FRR_CTL'
        request.num_props=4
        request.start_prop=0
        request.a_mode=a_mode
        request.b_mode=b_mode
        request.c_mode=c_mode
        request.d_mode=d_mode
        cmd = config_frr_cmd_s.build(request)
        self.spi.command(cmd, config_frr_cmd_s.name)
    #end def

    def disable_interrupt(self):
        """
        Disable radio chip hardware interrupt
        """
        if (gpio):
            GPIO.remove_event_detect(GPIO_NIRQ)
    #end def

    def dump_radio(self):
        """
        Dump all of the current radio decice property settings

        Since all SPI I/O operations are traced, this has the side effect that the
        dump is written out to the radio trace.
        A shadow of all of the property information is maintained by 'dump_strings'
        in memory and is returned by this call.
        """
        for gp_n, gp_s in radio_config_groups.iteritems():
            accumulator = 0
            prop = ''
            while (True):
                """
                accumulate entire property, repeating get_ for MAX_RADIO_RSP size
                until all pieces have been retrieved.
                """
                remainder = gp_s.sizeof() - accumulator
                chunk_size = remainder if (remainder < MAX_RADIO_RSP) else MAX_RADIO_RSP
                prop += self.get_property(radio_config_group_ids.parse(gp_n),
                                          accumulator, chunk_size)
                accumulator += chunk_size
                if (accumulator >= gp_s.sizeof()):
                    break
            self.dump_strings[gp_n] = prop
        self.dump_time = localtime()
        return self.dump_strings
    #end def

    def enable_interrupts(self):
        """
        Enable radio chip interrupts

        Callback function is defined when object was created. It is bound
        the interrupt and will be called when the GPIO transitions from
        high to low.
        """
        if (gpio):
            GPIO.add_event_detect(GPIO_NIRQ,
                                  GPIO.FALLING,
                                  callback=self.callback,
                                  bouncetime=100)
    #end def

    def  fast_all(self):
        """
        Get all four fast response registers
        """
        return fast_frr_s.parse(self.spi.read_frr(0, 4))
    #end def

    def fast_device_state(self):
        """
        Get current radio device state from fast read register
        """
        return Si446xNextStates_t(Byte('state')).parse(self.spi.read_frr(0, 1))
    #end def

    def fast_latched_rssi(self):
        """
        Get RSSI from fast read register

        The radio chip measures the receive signal strength (RSSI) during the
        beginning of receiving a packet, and latches this value.
        """
        return ord( self.spi.read_frr(3, 1))
    #end def

    def fast_modem_pend(self):
        """
        Get modem pending interrupt flags from fast read register
        """
        return modem_pend_s.parse(self.spi.read_frr(2, 1))
    #end def

    def fast_ph_pend(self):
        """
        Get packet handler (ph) pending interrupt flags from fast read register
        """
        return ph_pend_s.parse(self.spi.read_frr(1, 1))
    #end def

    def fifo_info(self, rx_flush=False, tx_flush=False):
        """
        Get the current tx/rx fifo depths and optionally flush

        Returns a list of [rx_fifo_count, tx_fifo_space]
        """
        request = fifo_info_cmd_s.parse('\x00' * fifo_info_cmd_s.sizeof())
        request.cmd='FIFO_INFO'
        request.state.rx_reset=rx_flush
        request.state.tx_reset=tx_flush
        cmd = fifo_info_cmd_s.build(request)
        self.spi.command(cmd, fifo_info_cmd_s.name)
        rsp = self.spi.response(fifo_info_rsp_s.sizeof(), fifo_info_rsp_s.name)
        if (rsp):
            response = fifo_info_rsp_s.parse(rsp)
            return [response.rx_fifo_count, response.tx_fifo_space]
        return None
    #end def

    def get_channel(self):
        """
        Get current radio channel
        """
        return self.channel
    #end def

    def get_chip_status(self):
        """
        Get current chip status

        No change to current pending interrupts.
        """
        request = get_chip_status_cmd_s.parse('\x00\xff')
        request.cmd = 'GET_CHIP_STATUS'
        cmd = get_chip_status_cmd_s.build(request)
        self.spi.command(cmd, get_chip_status_cmd_s)
        rsp = self.spi.response(get_chip_status_rsp_s.sizeof(), get_chip_status_rsp_s.name)
        if (rsp):
            self.trace.add('RADIO_PEND', rsp, s_name=get_chip_status_rsp_s.name, level=2)
            return (get_chip_status_rsp_s.parse(rsp))
        return None
    #end def

    def get_clear_interrupts(self, clr_flags=None):
        """
        Clear radio chip pending interrupts

        The interrupts to clear can be specified (clr_pending_int_s).
        If no clr_flags passed, then will clear all pending interrupts.

        Returns pending interrupt conditions existing prior to
        clear (int_status_rsp_s).

        Refer to structures defined by the Si4463 radio API revB1B.
        """
        self.clear_interrupts(clr_flags)
        rsp = self.spi.response(int_status_rsp_s.sizeof(), int_status_rsp_s.name)
        if (rsp):
            self.trace.add('RADIO_PEND', rsp, s_name=int_status_rsp_s.name, level=2)
            return (int_status_rsp_s.parse(rsp))
        return None
    #end def

    def get_config_lists(self):
        """
        Get list of radio configuration string generator functions

        Each item in the returned list is a pointer to a function
        that can be called successively to traverse the config
        strings in its list. The first call is passed zero to
        start with the first string in the list. Successive calls
        are passed the offset into the list for the next appropriate
        string (the sum of all previous string lengths). The
        list is terminated by a zero-length string.

        There are at least two configuration strings, one produced
        by the Silicon Labs WDS program. The other is defined
        in the platform configuration file that specifies details
        about this specific hardware instantiation (e.g., GPIO pin
        assignments). Each list consists of a set of Pascal-style
        strings that consist of a one byte length field followed
        by specified number of bytes (and NOT null-terminated like
        c-style strings). The list consists of zero or more strings
        concatenated together, terminating in a zero-length string.
        See radioconfig/si446xcfg.c for more details.
        """
        return [get_config_wds, get_config_local]
    #end def

    def get_cts(self):
        """
        Get current readiness radio chip command processor

        Read CTS, return true if high
        """
        rsp = _get_cts()
        return rsp
    #end def

    def get_gpio(self):
        """
        Get current state and configuration of radio chip GPIO pins
        """
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='GPIO_PIN_CFG'
        cmd = read_cmd_s.build(request)
        self.spi.command(cmd, read_cmd_s.name)
        rsp = self.spi.response(get_gpio_pin_cfg_rsp_s.sizeof(), get_gpio_pin_cfg_rsp_s.name)
        if (rsp):
            response = get_gpio_pin_cfg_rsp_s.parse(rsp)
            return response
        return None
    #end def

    def get_interrupts(self):
        """
        get current interrupt conditions

        doesn't clear any interrupts (set all flags to 1)
        """
        clr_flags = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
        return self.get_clear_interrupts(clr_flags)
    #end def

    def get_packet_info(self):
        """
        Get the length of the packet as received by the radio
        """
        request = packet_info_cmd_s.parse('\x00' * packet_info_cmd_s.sizeof())
        request.cmd='PACKET_INFO'
        request.field_num='NO_OVERRIDE'
        cmd = packet_info_cmd_s.build(request)
        self.spi.command(cmd, packet_info_cmd_s.name)
        rsp = self.spi.response(packet_info_rsp_s.sizeof(), packet_info_rsp_s.name)
        if (rsp):
            response = packet_info_rsp_s.parse(rsp)
            return response.length
        return None
    #end def

    def get_property(self, group, prop, len):
        """
        Read one or more contiguous radio chip properties

        Returns byte array since this is potentially only portion of a property group
        """
        request = get_property_cmd_s.parse('\x00' * get_property_cmd_s.sizeof())
        request.cmd='GET_PROPERTY'
        request.group=group
        request.num_props=len
        request.start_prop=prop
        cmd = get_property_cmd_s.build(request)
        self.spi.command(cmd, get_property_cmd_s.name)
        rsp = self.spi.response(17, get_property_rsp_s.name)
        if (rsp):
            response = get_property_rsp_s.parse(rsp)
            return bytearray(response.data)[:len]
        return None
    #end def

    def power_up(self):
        """
        Start up the Radio.
        """
        if (not _get_cts()):
            self.trace.add('RADIO_CHIP', 'cts not ready', level=2)
        request = power_up_cmd_s.parse('\x00' * power_up_cmd_s.sizeof())
        request.cmd='POWER_UP'
        request.boot_options.patch=False
        request.boot_options.func=1
        request.xtal_options.txcO=3
        request.xo_freq=4000000
        cmd = power_up_cmd_s.build(request)
        self.spi.command(cmd,  power_up_cmd_s.name)
    #end def

    def read_cmd_buff(self):
        """
        Read Clear-to-send (CTS) status via polling command over SPI

        Pull nsel low. read cts from cmd_buff. If cts=0xff, then
        pull nsel high and repeat. Else return copy of the command buf
        """
        rsp = self.spi.response(read_cmd_buff_rsp_s.sizeof(), read_cmd_buff_rsp_s.name)
        if (rsp):
            response = read_cmd_buff_rsp_s.parse(rsp)
    #end def

    def read_silicon_info(self):
        """
        Read silicon manufacturing information
        """
        response = []
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='PART_INFO'
        cmd = read_cmd_s.build(request)
        self.spi.command(cmd, read_cmd_s.name)
        rsp = self.spi.response(read_part_info_rsp_s.sizeof(),
                                 read_part_info_rsp_s.name)
        if (rsp):
            response.append((rsp, read_part_info_rsp_s.parse(rsp)))

            request.cmd='FUNC_INFO'
            cmd = read_cmd_s.build(request)
            self.spi.command(cmd, read_cmd_s.name)
            rsp = self.spi.response(read_func_info_rsp_s.sizeof(),
                                     read_func_info_rsp_s.name)
        if (rsp):
            response.append((rsp,read_func_info_rsp_s.parse(rsp)))
        return response
    #end def


    def read_rx_fifo(self, len):
        """
        Read data from the radio chip receive fifo
        returns bytesarray
        """
        return self.spi.read_fifo(len)
    #end def

    def set_channel(self, num):
        """
        Set radio channel
        """
        self.channel = num
    #end def

    def send_config(self, props):
        """
        Send a config string to the radio chip

        Already formatted into proper byte string with command and parameters
        """
        self.spi.command(props, set_property_cmd_s.name)
    #end def

    def set_property(self, pg, ps, pd):
        """
        Set one or more contiguous radio device properties

        Up to 12 properties at a time (msg buffer is 16, subtrace for
        cts and set_property_header). Higher level code would need to
        split up the data into more than one set_property call to set
        any group larger than 12 (like modem for instance).
        """
        if (len(pd) > MAX_GROUP_WRITE):
            self.trace.add('RADIO_ERROR',
                           'set property too long ({}:{}) ({})'.format(pg, ps, len(pd)))
        request = set_property_cmd_s.parse('\x00' * set_property_cmd_s.sizeof())
        request.cmd='SET_PROPERTY'
        request.group=pg
        request.num_props=len(pd)
        request.start_prop=ps
        cmd = set_property_cmd_s.build(request) + pd
        self.spi.command(cmd, set_property_cmd_s.name)
    #end def

    def set_power(self, level):
        """
        Set radio transmission power level (0x7f = 20dBm)
        """
        print("set_power",level,type(level))
        self.set_property('PA', 1, bytearray(level & 0x7f))
    #end def

    def shutdown(self):
        """
        Power off the radio chip.
        """
        self.trace.add('RADIO_CHIP',
                       'set GPIO pin {} (SI446x sdn disable)'.format(GPIO_SDN),
                       level=2)
        if (gpio):
            GPIO.output(GPIO_SDN,1)
            GPIO.cleanup()
    #end def

    def start_rx(self, len, channel=255):
        """
        Transition the radio chip to the receive enabled state
        """
        request = start_rx_cmd_s.parse('\x00' * start_rx_cmd_s.sizeof())
        request.cmd = 'START_RX'
        request.channel = self.channel if (channel == 255) else channel
        request.condition.start = 'IMMEDIATE'
        request.next_state1 = 'NOCHANGE'  # rx timeout
        request.next_state2 = 'READY'     # rx complete
        request.next_state3 = 'READY'     # rx invalid (bad CRC)
        request.rx_len= len
        cmd = start_rx_cmd_s.build(request)
        self.spi.command(cmd, start_rx_cmd_s.name)
    #end def

    def start_rx_short(self):
        """
        Transition the radio chip to the receive enabled state
        """
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='START_RX'
        cmd = read_cmd_s.build(request)
        self.spi.command(cmd, read_cmd_s.name)
    #end def

    def start_tx(self, len, channel=255):
        """
        Transition the radio chip to the transmit state.
        """
        request = start_tx_cmd_s.parse('\x00' * start_tx_cmd_s.sizeof())
        request.cmd='START_TX'
        request.channel = self.channel if (channel == 255) else channel
        request.condition.txcomplete_state='READY'
        request.condition.retransmit='NO'
        request.condition.start='IMMEDIATE'
        request.tx_len=len
        cmd = start_tx_cmd_s.build(request)
        self.spi.command(cmd,  start_tx_cmd_s.name)
    #end def

    def trace_radio(self):
        """
        Dump the saved radio chip configuration to the trace buffer
        """
        for k, v in self.dump_strings.iteritems():
            self.trace.add('RADIO_DUMP', v, s_name=radio_config_groups[k].name, level=2)
    #end def

    def unshutdown(self):
        """
        Power on the radio chip.

        Set GPIO pin 18 (GPIO23) connected to si446x.sdn
        """
        self.trace.add('RADIO_GPIO',
                       'clear GPIO pin {} (SI446x sdn enable)'.format(GPIO_SDN),
                       level=2)
        if (gpio):
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(GPIO_CTS,GPIO.IN)    #  [CTSn]
            GPIO.setup(GPIO_NIRQ,GPIO.IN)   #  [IRQ]
            GPIO.setup(GPIO_SDN,GPIO.OUT)   #  [sdn]
            GPIO.output(GPIO_SDN,1)         # make sure it is already shut down
            sleep(.1)
            GPIO.output(GPIO_SDN,0)
            sleep(.1)
    #end def

    def write_tx_fifo(self, dat):
        """
        Write data into the radio chip transmit fifo
        """
        self.spi.write_fifo(bytearray(dat))
    #end def

#end class

def si446xtrace_test_callback():
    print('tested radio callback')

def test_trace(radio, trace):
    for t in trace.rb.data:
        print(type(t[4]),t)

def test_radio(radio, trace):
    radio.unshutdown()
    radio.power_up()
    radio.config_frr()
    total = 0
    list_of_lists = radio.get_config_lists()
    for l in list_of_lists:
        print(l)
        x = 0
        while (True):
            s = l(x)
            if (not s): break
            if (s[0] != radio_config_cmd_ids.build('POWER_UP') and
                ((s[0] == radio_config_cmd_ids.build('SET_PROPERTY')) and
                      (s[1] != radio_config_group_ids.build('FRR_CTL')))):
                print('len({})    command({})    Group({})'.format(len(s), binascii.hexlify(s[0]), binascii.hexlify(s[1])))
                radio.send_config(s)
                total += len(s)
                status = radio.get_chip_status()
                if (status.chip_pend.CMD_ERROR):
                    print(status)
                    print(binascii.hexlify(s))
                    radio.clear_interrupts()
            x += len(s) + 1
    ss = radio.get_interrupts()
    print(ss)
    ss= radio.fast_all()
    print(ss)
    print(radio.dump_radio())

def si446xradio_test():
    import si446xtrace
    trace =  si446xtrace.Trace(100)
    radio = Si446xRadio(device=0, callback=si446xtrace_test_callback, trace=trace)
    test_radio(radio, trace)
    test_trace(radio, trace)
    return trace, radio

if __name__ == '__main__':
    t,r = si446xradio_test()

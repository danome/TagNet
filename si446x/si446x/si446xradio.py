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

##########################################################################
#
# _get_cts
#
def _get_cts():
    #print('.')
    if (gpio):
        return (GPIO.input(GPIO_CTS))
    else:
        return False

# _get_cts_wait
#
def _get_cts_wait(t):
    if (gpio):
        for i in range(t+1):
            r = _get_cts()
            if (r or (t == 0)):  return r
            sleep(.001)
    return False

##########################################################################
#
# common spi access routines
#
# note: spi device driver controls chip select

class SpiInterface:
    """class to access the Si446x over SPI interface"""
    def __init__(self, device, trace=None):
        print('init spi', device, trace)
        try:
            self.trace = trace if (trace) else si446xtrace.Trace(100)
            self.spi = spidev.SpiDev()
            self.spi.open(0, device)  # port=0, device(CS)=device_num
            #self.spi.max_speed_hz=600000
            print('spi max speed',self.spi.max_speed_hz)
        except IOError as e:
            print("Si446xRadio.__init__", e)

    def command(self, pkt, form):
        _get_cts_wait(100)
        if (not _get_cts()):
            print("spi_send_command: don't have cts")
        try:
            self.form = form
            self.trace.add('RADIO_CMD', pkt, form, level=2)
            self.spi.xfer2(list(bytearray(pkt)))
        except IOError as e:
            print("spi_send_command: ", e)

    def response(self, rlen, form):
        _get_cts_wait(100)
        rsp = ''
        if (not _get_cts()):
            print("spi_read_response: don't have cts")
        try:
            r = self.spi.xfer2([0x44] + MAX_RADIO_RSP * [0])
            rsp = ''.join([chr(item) for item in r[1:rlen+2]])
            form = form if (form) else self.form
            self.trace.add('RADIO_RSP', rsp, form, level=2)
        except IOError as e:
            print("spi_read_response", e)
        return rsp

    def read_fifo(self, rlen):
        if (rlen > RX_FIFO_MAX):
            print("read_fifo_too_long", rlen)
        r = self.spi.xfer2([0x77] + rlen * [0])
        self.trace.add('RADIO_RX_FIFO', str(rlen), None, level=2)
        return r[1:]

    def write_fifo(self, buf):
        if (len(buf) > TX_FIFO_MAX):
            print("write_fifo_too_long", buf)
        self.trace.add('RADIO_TX_FIFO', str(len(buf)), None, level=2)
        r = self.spi.xfer2([0x66] + buf)

    def read_frr(self, off, len):
        index = [0,1,3,7]
        if (len > 4):
            print("read_frr too long", off, len)        
        r = self.spi.xfer2([0x50 + index[off]] + len * [0])
        rsp = ''.join([chr(item) for item in r[1:len+1]])
        self.trace.add('RADIO_FRR', rsp, fast_frr_rsp_s.name, level=2)
        return rsp
#end class

# _gpio_callback
#
def _gpio_callback(channel):
    print('Edge detected on channel %s'%channel)

##########################################################################
#
# class Si446xRadio - radio device access and control routines
#
class Si446xRadio(object):
    """ class for handling low level Radio device control"""
    def __init__(self, device=0, callback=_gpio_callback, trace=None):
        print('init radio', device, callback, trace)
        self.trace = trace if (trace) else si446xtrace.Trace(100)
        self.channel = 0
        self.callback = callback
        self.dump_strings = {}
        self.spi = SpiInterface(device, trace=self.trace)
    #end def

    # change_state - force radio chip to change to specific state.
    #
    #  waits (ms) for acknowledgement that radio has processed the change
    #
    def change_state(self, state,  wait=0):
        request = change_state_cmd_s.parse('\x00' * change_state_cmd_s.sizeof())
        request.cmd = 'CHANGE_STATE'
        request.state = state
        cmd = change_state_cmd_s.build(request)
        self.spi.command(cmd, change_state_cmd_s.name)
        _get_cts_wait(wait)
    #end def

    # check_CCA - Perform Clear Channel Assessment.
    #
    def check_CCA(self):
        rssi = self.fast_latched_rssi()
        return True if (rssi < si446x_cca_threshold) else False
    #end def

    # clear_interrupts() - Clear radio chip pending interrupts
    #
    # default (nothing in clr_flags) then clear all interrupts
    #
    def clear_interrupts(self, clr_flags=None):
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='GET_INT_STATUS'
        #print request
        cf = clr_pend_int_s.build(clr_flags) if (clr_flags) else ''
        cmd = read_cmd_s.build(request) + cf
        #print('clear_ints', cmd.encode('hex'), clr_flags)
        self.spi.command(cmd, read_cmd_s.name)
    #end def

    # config_frr - Configure the Fast Response Registers to the expected values
    #
    # Configures the radio chip to return the specific values used by the Driver.
    #
    # const uint8_t si446x_frr_config[] = { 0x11, 0x02, 0x04, 0x00,
    #				            0x09, 0x04, 0x06, 0x0a
    #                                    };
    # frr is set manually right after POWER_UP
    #
    #   A: device state
    #   B: PH_PEND
    #   C: MODEM_PEND
    #   D: Latched_RSSI
    #
    # We use LR (Latched_RSSI) when receiving a packet.  The RSSI value is
    # attached to the last RX packet.  The Latched_RSSI value may, depending on
    # configuration, be associated with some number of bit times once RX is enabled
    # or when SYNC is detected.
    #
    def config_frr(self):
        request = config_frr_cmd_s.parse('\x00' * config_frr_cmd_s.sizeof())
        request.cmd='SET_PROPERTY'
        request.group='FRR_CTL'
        request.num_props=4
        request.start_prop=0
        request.a_mode='CURRENT_STATE'
        request.b_mode='INT_PH_PEND'
        request.c_mode='INT_MODEM_PEND'
        request.d_mode='LATCHED_RSSI'
        #print request
        cmd = config_frr_cmd_s.build(request)
        self.spi.command(cmd, config_frr_cmd_s.name)
    #end def

    # disableInterrupt - Disable radio chip hardware interrupt
    #
    #
    def disable_interrupt(self):
        if (gpio):
            GPIO.remove_event_detect(GPIO_NIRQ)
    #end def

    # dump_radio - Dump all of the current radio chip configuration
    #
    def dump_display(self):
        for k, v in self.dump_strings.iteritems():
            s = '{}, {}'.format(k, radio_config_groups[k].parse(v))
            self.trace.add('RADIO_DUMP', s)

    # dump_radio - Dump all of the current radio chip configuration
    #
    def dump_radio(self):
        for gp_n, gp_s in radio_config_groups.iteritems():
            i = 0
            s = ''
            while (True):
                r = gp_s.sizeof() - i
                x = r if (r < MAX_RADIO_RSP) else MAX_RADIO_RSP
#                p = self.get_property(gp_n, i, x)
                p = self.get_property(radio_config_group_ids.parse(gp_n), i, x)
                #print p
                s += p
                i += x
                if (i >= gp_s.sizeof()):
                    break
            self.dump_strings[gp_n] = s
            self.dump_time = localtime()
    #end def

    # enable_interrupts - Enable radio chip interrupts
    #
    def enable_interrupts(self):
        if (gpio):
            GPIO.add_event_detect(GPIO_NIRQ,
                                  GPIO.FALLING,
                                  callback=self.callback,
                                  bouncetime=100)
    #end def

    # fast_all - Read all four fast response registers
    #
    def  fast_all(self):
        return self.spi.read_frr(0, 4)
    #end def
     
    # fast_device_state - Get current state of the radio chip from fast read register
    #
    #command uint8_t()
    #.
    def fast_device_state(self):
        return ord(self.spi.read_frr(0, 1))
    #end def

    # fast_latched_rssi - get RSSI from fast read register 
    #
    # The radio chip measures the receive signal strength (RSSI) during the
    # beginning of receiving a packet, and latches this value.
    #
    def fast_latched_rssi(self):
        return ord( self.spi.read_frr(3, 1))
    #end def

    # fast_modem_pend - get modem pending interrupt flags from fast read register
    #
    def fast_modem_pend(self):
        return ord(self.spi.read_frr(2, 1))
    #end def

    # fast_modem_pend - get modem pending interrupt flags from fast read register
    #
    def fast_ph_pend(self):
        return ord(self.spi.read_frr(1, 1))
    #end def

    # fifo_info - Get the current tx/rx fifo depths and optionally flush
    #
    # return a list of [rx_fifo_count, tx_fifo_space]
    #
    def fifo_info(self, rx_flush=False, tx_flush=False):
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

    # get_channel get current radio channel
    #
    def get_channel(self):
        return self.channel
    #end def

    # get_config_lists - Get a list of configuration lists
    #
    # each list is consists of concatenated pascal strings, each presenting
    # a command string for configuring radio chip properties
    #
    def get_config_lists(self):
        return [get_config_wds, get_config_local]
    #end def
    
    # get_cts - Get current readiness radio chip command processor
    #
    def get_cts(self):
        # read CTS, return true if high
        rsp = _get_cts()
        return rsp
    #end def

    # get_clear_interrupts - status and clear are done in one operation
    #
    def get_clear_interrupts(self, clr_flags=None):
        self.clear_interrupts(clr_flags)
        rsp = self.spi.response(int_status_rsp_s.sizeof(), int_status_rsp_s.name)
        if (rsp):
            return (int_status_rsp_s.parse(rsp))
        return None
    #end def

    # get_interrupts() - get current interrupt conditions
    #                     doesn't clear any interrupts
    #
    def get_interrupts(self):
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='GET_INT_STATUS'
        # don't clear any interrupts (set all flags to 1)
        cf = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
        clr_flags = clr_pend_int_s.build(cf)
        cmd = read_cmd_s.build(request) + clr_flags
        self.spi.command(cmd, read_cmd_s.name)
        rsp = self.spi.response(int_status_rsp_s.sizeof(), int_status_rsp_s.name)
        if (rsp):
            return (int_status_rsp_s.parse(rsp))
        return None
    #end def

    # get_packet_info - 
    #
    def get_packet_info(self):
        request = packet_info_cmd_s.parse('\x00' * packet_info_cmd_s.sizeof())
        request.cmd='PACKET_INFO'
        request.field_num='NO_OVERRIDE'
        cmd = packet_info_cmd_s.build(request)
        self.spi.command(cmd, packet_info_cmd_s.name)
        rsp = self.spi.response(packet_info_rsp_s.sizeof(), packet_info_rsp_s.name)
        if (rsp):
            response = packet_info_rsp_s.parse(rsp)
            #print response
            return response.length
        return None
    #end def

    # get_property - Read one or more contiguous radio chip properties
    #
    #
    def get_property(self, group, prop, len):
        request = get_property_cmd_s.parse('\x00' * get_property_cmd_s.sizeof())
        request.cmd='GET_PROPERTY'
        request.group=group
        request.num_props=len
        request.start_prop=prop
        #print request
        cmd = get_property_cmd_s.build(request)
        self.spi.command(cmd, get_property_cmd_s.name)
        rsp = self.spi.response(17, get_property_rsp_s.name)
        if (rsp):
            response = get_property_rsp_s.parse(rsp)
            #print response
            return str(bytearray(response.data))
        return None
    #end def

    # get_clear_interrupts() - Clear radio chip pending interrupts
    #                           and return current interrupt conditions
    #  power_up - Turn radio chip power on.
    #
    def power_up(self):
        if (not _get_cts()):
            print("power_up: cts not ready")
        request = power_up_cmd_s.parse('\x00' * power_up_cmd_s.sizeof())
        request.cmd='POWER_UP'
        request.boot_options.patch=False
        request.boot_options.func=1
        request.xtal_options.txcO=3
        request.xo_freq=4000000
        #print request
        cmd = power_up_cmd_s.build(request)
        self.spi.command(cmd,  power_up_cmd_s.name)
    #end def

    #  read_cmd_buff - read Clear-to-send (CTS) status via polling command over SPI
    #
    #  pull nsel low. send command. read cts and cmd_buff.
    #  if cts=0xff, then pull nsel high and repeat.
    #
    def read_cmd_buff(self):
        rsp = self.spi.response(read_cmd_buff_rsp_s.sizeof(), read_cmd_buff_rsp_s.name)
        if (rsp):
            response = read_cmd_buff_rsp_s.parse(rsp)
            #print response
    #end def

    # read_silicon_id - read silicon manufacturing information
    #
    def read_silicon_info(self):
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='PART_INFO'
        #print request
        cmd = read_cmd_s.build(request)
        self.spi.command(cmd, read_cmd_s.name)
        rsp = self.spi.response(read_part_info_rsp_s.sizeof(), read_part_info_rsp_s.name)
        if (rsp):
            response = read_part_info_rsp_s.parse(rsp)
            #print response
        request.cmd='FUNC_INFO'
        #print request
        cmd = read_cmd_s.build(request)
        self.spi.command(cmd, read_cmd_s.name)
        rsp = self.spi.response(read_func_info_rsp_s.sizeof(), read_func_info_rsp_s.name)
        if (rsp):
            response = read_func_info_rsp_s.parse(rsp)
            #print response
    #end def


    # read_rx_fifo - Read data from the radio chip receive fifo
    #
    # return bytestring
    #
    def read_rx_fifo(self, len):
        return self.spi.read_fifo(len)
    #end def

    # send_config - Send a config string to the radio chip
    #
    # already formatted into proper byte string with command and parameters
    #
    def send_config(self, props):
        self.spi.command(props, set_property_cmd_s.name)
    #end def

    # set_channel - set radio channel
    #
    def set_channel(self, num):
        self.channel = num
    #end def

    # set_property - set one or more contiguous radio chip properties
    #
    # need to add command header
    #
    def set_property(self, pg, ps, pd):
        request = set_property_cmd_s.parse('\x00' * set_property_cmd_s.sizeof())
        request.cmd='SET_PROPERTY'
        request.group=pg
        request.num_props=len(pd)
        request.start_prop=ps
        #print(request, pg, ps, pd.encode('hex'))
        cmd = set_property_cmd_s.build(request) + pd
        self.spi.command(cmd, set_property_cmd_s.name)
    #end def

    # shutdown - Power off the radio chip.
    #
    #  async command void    HW.si446x_shutdown()        { SI446X_SDN = 1; }
    #
    def shutdown(self):
        print('set GPIO pin %i (SI446x sdn disable)'%GPIO_SDN)
        if (gpio):
            GPIO.output(GPIO_SDN,1)
            GPIO.cleanup()
    #end def

    # start_rx() - Transition the radio chip to the receive enabled state
    #
    def start_rx(self, len, channel=255):
        request = start_rx_cmd_s.parse('\x00' * start_rx_cmd_s.sizeof())
        request.cmd='START_RX'
        request.channel = self.channel if (channel == 255) else channel
        request.condition.start='IMMEDIATE'
        # all next_state fields left set to default (nochange)
        request.rx_len=len
        cmd = start_rx_cmd_s.build(request)
        self.spi.command(cmd, start_rx_cmd_s.name)
    #end def

    # start_rx_short - Transition the radio chip to the receive enabled state
    #
    def start_rx_short(self):
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='START_RX'
        #print request
        cmd = read_cmd_s.build(request)
        self.spi.command(cmd, read_cmd_s.name)
    #end def

    # start_tx
    #Transition the radio chip to the transmit state.
    def start_tx(self, len, channel=255):
        request = start_tx_cmd_s.parse('\x00' * start_tx_cmd_s.sizeof())
        request.cmd='START_TX'
        request.channel = self.channel if (channel == 255) else channel
        request.condition.txcomplete_state='READY'
        request.condition.retransmit='NO'
        request.condition.start='IMMEDIATE'
        request.tx_len=len
        #print request
        cmd = start_tx_cmd_s.build(request)
        self.spi.command(cmd,  start_tx_cmd_s.name)
    #end def

    # trace - add entry to global trace
    #
    def trace(self, where, what):
        pass
    #end def

    # trace_radio_pend - Trace the radio pending status, using fast registers
    #
    def trace_radio_pend(self):
        pass
    #end def

    # unshutdown - Power on the radio chip.
    #
    #  async command void    HW.si446x_unshutdown()      { SI446X_SDN = 0; }
    #
    def unshutdown(self):
        # set GPIO pin 18 (GPIO23) connected to si446x.sdn
        print('clear GPIO pin %i (SI446x sdn enable)'%GPIO_SDN)
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
    # write_tx_fifo - Write data into the radio chip transmit fifo
    #
    def write_tx_fifo(self, dat):
        self.spi.write_fifo(dat)
    #end def

#end class

from time import sleep

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



##########################################################################
#
# common spi access routines

# _spi_send_command
#
def _spi_send_command(spi, pkt):
    print 'spi_send: ' + pkt.encode('hex')
    _get_cts_wait(10)
    if (not _get_cts()):
        print("spi_send don't have cts")
    try:
        spi.xfer2(list(bytearray(pkt)))
    except IOError as e:
        print("spi_send_command", e)
#  call SpiBlock.transfer((void *) c, rsp, cl);

# _spi_read_response
#
def _spi_read_response(spi, rlen):
    _get_cts_wait(10)
    rsp = ''
    if (not _get_cts()):
        print("spi_read don't have cts")
    try:
        #write 'READ_CMD_BUFF' and read back cts as well as
        #response bytes
        r = spi.xfer2([0x44] + 16 * [0])
        rsp = ''.join([chr(item) for item in r[1:rlen+2]])
        print rsp.encode('hex')
    except IOError as e:
        print("spi_read_response", e)
    return rsp

# _get_cts
#
def _get_cts():
    print('.')
    if (gpio):
        return (GPIO.input(16))
    else:
        return False

# _get_cts_wait
#
def _get_cts_wait(t):
    if (gpio):
        for i in range(t+1):
            r = _get_cts()
            if (r or (t == 0)):  return r
            sleep(.01)
    return False

# _spi_read_fifo
#
def _spi_read_fifo(spi, rlen):
    if (rlen > 64):
        print("read_fifo_too_long", rlen)
    r = spi.xfer2([0x77] + rlen * [0])
    rsp = ''.join([chr(item) for item in r[1:rlen+1]])
    return rsp

# _spi_write_fifo
#
def _spi_write_fifo(spi, buf):
    if (len(buf) > 64):
        print("write_fifo_too_long", buf)
    r = spi.xfer2([0x66] + list(bytearray(buf)))

# _spi_read_frr
#
def _spi_read_frr(spi, off, len):
    index = [0,1,3,7]
    if (len > 4):
        print("read_frr too long", off, len)        
    r = spi.xfer2([0x50 + index[off]] + len * [0])
    rsp = ''.join([chr(item) for item in r[1:len+1]])
    return rsp

    
##########################################################################
#
# class Si446xRadio - radio device access and control routines
#
class Si446xRadio(object):
    #
    def __init__(self, device_num=0):
        if (gpio):
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(16,GPIO.IN)   #  [CTSn]
            GPIO.setup(22,GPIO.IN)   #  [IRQ]
            GPIO.setup(18,GPIO.OUT)  #  [sdn]
        self.spi = spidev.SpiDev()
        self.channel = 0
        try:
            self.spi.open(0, device_num)  # port=0, device(CS)=device_num
        except IOError as e:
            print("Si446xRadio.__init__", e)
        # spi device driver handles enabling chip select
    #end def


    # change_state - force radio chip to change to specific state.
    #
    def change_state(self, state,  wait):
        request = change_state_cmd_s.parse('\x00' * change_state_cmd_s.sizeof())
        request.cmd = 'CHANGE_STATE'
        request.state = state
        print request
        cmd = change_state_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
        _get_cts_wait(10)
    #end def

        
    # check_CCA - Perform Clear Channel Assessment.
    #
    def check_CCA(self):
        rssi = self.fast_latched_rssi()
        return True if (rssi < si446x_cca_threshold) else False
    #end def


    #
    #
    #
    # clr_cs - Clear radio chip select. [deprecated]
    #
    #def clr_cs(self):
    #    pass


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
        request.group=0x02
        request.num_props=4
        request.start_prop=0
        request.a_mode='CURRENT_STATE'
        request.b_mode='INT_PH_PEND'
        request.c_mode='INT_MODEM_PEND'
        request.d_mode='LATCHED_RSSI'
        print request
        cmd = config_frr_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
        if (not _get_cts()):
            print("config_frr: fyi cts not ready after command sent")        
    #end def
        

    #
    #
    #
    # disableInterrupt - Disable radio chip hardware interrupt
    #
    #
    def disable_interrupt(self):
        pass
    #end def


    #
    #
    #
    # dump_radio - Dump all of the current radio chip configuration
    #
    def dump_radio(self):
        pass
    #end def


    #
    #
    #
    # enableInterrupt - Enable radio chip interrupt
    #
    def enble_interrupt(self):
        pass
    #end def


    # fast_all - Read all four fast response registers
    #
    def  fast_all(self):
        return _spi_read_frr(self.spi, 0, 4)
    #end def

     
    # fast_device_state - Get current state of the radio chip from fast read register
    #
    #command uint8_t()
    #.
    def fast_device_state(self):
        return _spi_read_frr(self.spi, 0, 1)
    #end def


    # fast_latched_rssi - get RSSI from fast read register 
    #
    # The radio chip measures the receive signal strength (RSSI) during the
    # beginning of receiving a packet, and latches this value.
    #
    def fast_latched_rssi(self):
        return _spi_read_frr(self.spi, 3, 1)
    #end def


    # fast_modem_pend - get modem pending interrupt flags from fast read register
    #
    def fast_modem_pend(self):
        return _spi_read_frr(self.spi, 2, 1)
    #end def


    # fast_modem_pend - get modem pending interrupt flags from fast read register
    #
    def fast_ph_pend(self):
        return _spi_read_frr(self.spi, 1, 1)
    #end def


    # fifo_info - Get the current tx/rx fifo depths and optionally flush
    #
    # return a list of [rx_fifo_count, tx_fifo_space]
    #
    def fifo_info(self, rx_flush=False, tx_flush=False):
        request = fifo_info_cmd_s.parse('\x00' * fifo_info_cmd_s.sizeof())
        request.cmd='FIFO_INFO'
        request.rx=rx_flush
        request.tx=tx_flush
        print request
        cmd = fifo_info_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
        rsp = _spi_read_response(self.spi,
                                fifo_info_rsp_s.sizeof())
        if (rsp):
            response = fifo_info_rsp_s.parse(rsp)
            print response
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
        print 'GPIO pin 16 read (SI446x cts pin)', rsp
        return rsp
    #end def


    # get_packet_info - 
    #
    def get_packet_info(self):
        request = packet_info_cmd_s.parse('\x00' * packet_info_cmd_s.sizeof())
        request.cmd='PACKET_INFO'
        request.field_num='NO_OVERRIDE'
        print request
        cmd = packet_info_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
        rsp = _spi_read_response(self.spi,
                                packet_info_rsp_s.sizeof())
        if (rsp):
            response = packet_info_rsp_s.parse(rsp)
            print response
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
        print request
        cmd = get_property_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
        rsp = _spi_read_response(self.spi,
                                  get_property_rsp_s.sizeof())
        if (rsp):
            response = get_property_rsp_s.parse(rsp)
            print response
            return response.data
        return None
    #end def


    # clear_interrupts() - Clear all of the radio chip pending interrupts
    #
    def clear_interrupts(self, ph, modem, chip):
        pass
    #end def

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
        print request
        cmd = power_up_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
    #end def


    #  read_cmd_buff - read Clear-to-send (CTS) status via polling command over SPI
    #
    #  pull nsel low. send command. read cts and cmd_buff.
    #  if cts=0xff, then pull nsel high and repeat.
    #
    def read_cmd_buff(self):
        rsp = _spi_read_response(self.spi, read_cmd_buff_rsp_s.sizeof())
        if (rsp):
            response = read_cmd_buff_rsp_s.parse(rsp)
            print response
    #end def


    # read_silicon_id - read silicon manufacturing information
    #
    def read_silicon_info(self):
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='PART_INFO'
        print request
        cmd = read_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
        rsp = _spi_read_response(self.spi,
                                  read_part_info_rsp_s.sizeof())
        if (rsp):
            response = read_part_info_rsp_s.parse(rsp)
            print response
        request.cmd='FUNC_INFO'
        print request
        cmd = read_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
        rsp = _spi_read_response(self.spi,
                                  read_func_info_rsp_s.sizeof())
        if (rsp):
            response = read_func_info_rsp_s.parse(rsp)
            print response
    #end def


    # read_rx_fifo - Read data from the radio chip receive fifo
    #
    # return bytestring
    #
    def read_rx_fifo(self, len):
        return _spi_read_fifo(self.spi, len)
    #end def


    # send_config - Send a config string to the radio chip
    #
    # already formatted into proper byte string with command and parameters
    #
    def send_config(self, props):
        _spi_send_command(self.spi, props)
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
    def set_property(self, props):
        request = set_property_cmd_s.parse('\x00' * set_property_cmd_s.sizeof())
        request.cmd='SET_PROPERTY'
        print request
        cmd = set_property_cmd_s.build(request) + props
        _spi_send_command(self.spi, cmd)
    #end def


    # shutdown - Power off the radio chip.
    #
    #  async command void    HW.si446x_shutdown()        { SI446X_SDN = 1; }
    #
    def shutdown(self):
        print 'set GPIO pin 18 (SI446x sdn pin)'
        if (gpio):
            GPIO.output(18,1)
    #end def


    # start_rx() - Transition the radio chip to the receive enabled state
    #
    def start_rx(self, len, channel=255):
        request = start_rx_cmd_s.parse('\x00' * start_rx_cmd_s.sizeof())
        request.cmd='START_RX'
        request.channel = self.channel if (channel != 255) else channel
        request.condition.start='IMMEDIATE'
        # all next_state fields left set to default nochange
        request.rx_len=len
        print request
        cmd = start_rx_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
    #end def


    # start_rx_short - Transition the radio chip to the receive enabled state
    #
    def start_rx_short():
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='START_RX'
        print request
        cmd = read_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
    #end def


    # start_tx
    #Transition the radio chip to the transmit state.
    def start_tx(self, len, channel):
        request = start_tx_cmd_s.parse('\x00' * start_tx_cmd_s.sizeof())
        request.cmd='START_TX'
        request.channel=channel
        request.condition.txcomplete_state='READY'
        request.condition.retransmit='NO'
        request.condition.start='IMMEDIATE'
        request.tx_len=len
        print request
        cmd = start_tx_cmd_s.build(request)
        _spi_send_command(self.spi, cmd)
    #end def


    # trace - add entry to global trace
    #
    def trace(self, where, what):
        pass
    #end def


    # trace_radio_pend - Trace the radio pending status, using fast registers
    #
    def trace_radio_pend():
        pass
    #end def


    # unshutdown - Power on the radio chip.
    #
    #  async command void    HW.si446x_unshutdown()      { SI446X_SDN = 0; }
    #
    def unshutdown(self):
        # set GPIO pin 18 (GPIO23) connected to si446x.sdn
        print 'clear GPIO pin 18 (SI446x sdn pin)'
        if (gpio):
            GPIO.output(18,1)             # make sure it is already shut down
            sleep(0.1)
            GPIO.output(18,0)
            sleep(0.1)
    #end def

    # write_tx_fifo - Write data into the radio chip transmit fifo
    #
    def write_tx_fifo(dat):
        _spi_write_fifo(self.spi, dat)
    #end def

#end class

from time import sleep

from construct import *

import spidev

try:
    import RPi.GPIO as GPIO
    gpio = True
except RuntimeError as e:
    gpio = False
    print(e)

from si446xdef import Si446xCmds_t

#
# 0x00
# ox01
# 0x02
# 0x03
# 0x04
# 0x05
# 0x06
# 0x07
# 0x08
# 0x09


##########################################################################
#
# common spi access routines

# _spi_send_command
#
def _spi_send_command(spi, pkt):
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
    except IOError as e:
        print("spi_read_response", e)
    return rsp


def _get_cts():
    if (gpio):
        return (GPIO.input(16))
    else:
        return False

def _get_cts_wait(t):
    if (gpio):
        for i in range(t):
            r = _get_cts()
            if (r):  return r
            sleep(.01)
            print('.')
    return False


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
        try:
            self.spi.open(0, device_num)  # port=0, device(CS)=device_num
        except IOError as e:
            print("Si446xRadio.__init__", e)
#  call Si446xCmd.clr_cs();

    # change_state - force radio chip to change to specific state.
    #
    def change_state(self, state,  wait):
        pass
    
    # check_CCA - Perform Clear Channel Assessment.
    #
    
    def check_CCA(self):
        pass
    
    # clr_cs - Clear radio chip select.
    #
    #def clr_cs(self):
    #    pass

    # config_frr - Configure the Fast Response Registers to the expected values
    #
    # Configures the radio chip to return the specific values used by the Driver.
    #
    def config_frr(self):
        pass

    # disableInterrupt - Disable radio chip hardware interrupt.
    #
    #
    def disableInterrupt(self):
        pass

    #
    #
    #
    #command void dump_radio()
    #Dump all of the current radio chip configuration.

    #
    #
    #
    #command void enableInterrupt()
    #Enable radio chip interrupt.

    #
    #
    #
    #command void fast_all(uint8_t *status)
    #Read all four fast response registers

    #
    #
    #
    #command uint8_t fast_device_state()
    #Get current state of the radio chip using fast read register.

    #
    #
    #
    #command uint8_t fast_latched_rssi()
    #Read the fast response register that holds radio receive signal strength indicator The radio chip measures the receive signal strength during the beginning of receiving a packet, and latches this value.

    #
    #
    #
    #command uint8_t fast_modem_pend()
    #Read the fast response register that holds modem pending interrupt flags

    #
    #
    #
    #command uint8_t fast_ph_pend()
    #Read the fast response register that holds packet handler pending interrupt flags

    #
    #
    #
    #command void fifo_info(uint16_t *rxp, uint16_t *txp, uint8_t flush_bits)
    #Get information about the current tx/rx fifo depths and optionally flush.

    #
    #
    #
    #command uint8_t **get_config_lists()
    #Get a list of configuration lists.

    # get_cts - Get current readiness radio chip command processor
    #
    def get_cts(self):
        # read CTS, return true if high
        rsp = _get_cts()
        print 'GPIO pin 16 read (SI446x cts pin)', rsp
        return rsp

    #
    #
    #
    #command uint16_t get_packet_info()
    #Read the fast response register that holds modem pending interrupt flags

    #
    #
    #
    #command void ll_clr_ints()
    #Clear all of the radio chip pending interrupts.

    #
    #
    #
    #command void ll_getclr_ints(si446x_int_state_t *intp)
    #Clear all of the radio chip pending interrupts return pending status (prior to clear).

    #
    #  power_up - Turn radio chip power on.
    #
    # command=
    # ox00  cmd=Si446xCmds.POWER_UP
    # ox01  boot_options=[patch(7)patch=NO_PATCH(0), (5:0)FUNC=PRO(1)]
    # 0x02  xtal_options=[(0)TCXO=XTAL(0)]
    # 0x03  xofreq=0x01C9C380  x0[31:24]
    # 0x04                     XO_FREQ[23:16]
    # 0x05                     XO_FREQ[15:8]
    # 0x06                     XO_FREQ[7:0]
    #
    # response=
    # 0x00  cts=  0xff=NOT_READY
    #
    def power_up(self):
        power_up_cmd_s = Struct('power_up_cmd_s',
                                Si446xCmds_t(UBInt8("cmd")),
                                BitStruct('boot_options',
                                          Flag('patch'),
                                          Padding(1),
                                          BitField('func',6)
                                ),
                                BitStruct('xtal_options',
                                          Padding(6),
                                          BitField('txcO', 2)
                                ),
                                UBInt32('xo_freq')
        )
        power_up_rsp_s = Struct('power_up_rsp_s',
                                Byte('cts')
        )
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
        print cmd.encode('hex')
        _spi_send_command(self.spi, cmd)
        if (not _get_cts()):
            print("power_up: fyi cts not ready after command sent")        
    #end def



    #  read_cmd_buff - read Clear-to-send (CTS) status via polling command over SPI
    #
    #  pull nsel low. send command. read cts and cmd_buff.
    #  if cts=0xff, then pull nsel high and repeat.
    #
    def read_cmd_buff(self):
        read_cmd_buff_rsp_s = Struct('read_cmd_buff_rsp_s',
			             Byte('cts'),
			             Field('cmd_buff', lambda ctx: 15)
	)
        rsp = _spi_read_response(self.spi, read_cmd_buff_rsp_s.sizeof())
        if (rsp):
            response = read_cmd_buff_rsp_s.parse(rsp)
            print response
            print rsp.encode('hex')
    #end def


    # read_silicon_id - read silicon manufacturing information
    #
    def read_silicon_info(self):
        read_cmd_s = Struct('read_cmd_s',
                            Si446xCmds_t(UBInt8("cmd")),
        )
        read_part_info_rsp_s = Struct('read_part_info_rsp_s',
                                      Byte('cts'),
                                      Byte('chiprev'),
                                      UBInt16('part'),
                                      Byte('pbuild'),
                                      UBInt16('id'),
                                      Byte('customer'),
                                      Byte('romid'),
        )
        read_func_info_rsp_s = Struct('read_func_info_rsp_s',
                                      Byte('cts'),
                                      Byte('revext'),
                                      Byte('revbranch'),
                                      Byte('revint'),
                                      UBInt16('patch'),
                                      Byte('func'),
        )
        request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
        request.cmd='PART_INFO'
        print request
        cmd = read_cmd_s.build(request)
        print cmd.encode('hex')
        _spi_send_command(self.spi, cmd)
        rsp = _spi_read_response(self.spi,
                                  read_part_info_rsp_s.sizeof())
        if (rsp):
            response = read_part_info_rsp_s.parse(rsp)
            print response
            print rsp.encode('hex')
        request.cmd='FUNC_INFO'
        print request
        cmd = read_cmd_s.build(request)
        print cmd.encode('hex')
        _spi_send_command(self.spi, cmd)
        rsp = _spi_read_response(self.spi,
                                  read_func_info_rsp_s.sizeof())
        if (rsp):
            response = read_func_info_rsp_s.parse(rsp)
            print response
            print rsp.encode('hex')
        
    #
    #
    #
    #command void read_property(uint16_t p_id, uint16_t num, uint8_t *rsp_p)
    #Read one or more contiguous radio chip properties

    #
    #
    #
    #command void read_rx_fifo(uint8_t *data, uint8_t length)
    #Read data from the radio chip receive fifo.

    #
    #
    #
    #command void send_config(uint8_t *properties, uint16_t length)
    #Send a config string to the radio chip.

    #
    #
    #
    #command void set_property(uint16_t prop, uint8_t *values, uint16_t vl)
    #set one or more contiguous radio chip properties

    # shutdown - Power off the radio chip.
    #
    #  async command void    HW.si446x_shutdown()        { SI446X_SDN = 1; }
    #
    def shutdown(self):
        print 'set GPIO pin 18 (SI446x sdn pin)'
        if (gpio):
            GPIO.output(18,1)

    #
    #
    #
    #command void start_rx()
    #Transition the radio chip to the receive enabled state.

    #
    #
    #
    #command void start_rx_short()
    #Transition the radio chip to the receive enabled state.

    #
    #
    #
    #command void start_tx(uint16_t len)
    #Transition the radio chip to the transmit state.

    #
    #
    #
    #command void trace_radio_pend(uint8_t *pend)
    #Read the radio pending status, using fast registers.

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

    #
    #
    #
    #command void write_tx_fifo(uint8_t *data, uint8_t length)
    #Write data into the radio chip transmit fifo.

#end class

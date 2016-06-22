from construct import *

try:
    bytes
except NameError:
    bytes = str

#Si446xCmds_t = Enum(UBInt8('CMD'),

#def Si446xCmds_t(code):
#    return Enum(code,
def Si446xCmds_t(code):
    return Enum(code,
                NOP                    = 0,
                POWER_UP               = 0x02,
                PART_INFO              = 0x01,
                FUNC_INFO              = 0x10,
                SET_PROPERTY           = 0x11,
                GET_PROPERTY           = 0x12,
                GPIO_PIN_CFG           = 0x13,
                FIFO_INFO              = 0x15,
                GET_INT_STATUS         = 0x20,
                REQUEST_DEVICE_STATE   = 0x33,
                CHANGE_STATE           = 0x34,
                READ_CMD_BUFF          = 0x44,
                FRR_A_READ             = 0x50,
                FRR_B_READ             = 0x51,
                FRR_C_READ             = 0x53,
                FRR_D_READ             = 0x57,
                IRCAL                  = 0x17,
                IRCAL_MANUAL           = 0x1a,
                START_TX               = 0x31,
                WRITE_TX_FIFO          = 0x66,
                PACKET_INFO            = 0x16,
                GET_MODEM_STATUS       = 0x22,
                START_RX               = 0x32,
                RX_HOP                 = 0x36,
                READ_RX_FIFO           = 0x77,
                GET_ADC_READING        = 0x14,
                GET_PH_STATUS          = 0x21,
                GET_CHIP_STATUS        = 0x23,
    )
#end def

def Si446xPropsEnum(subcon):
        return Enum(subcon,
                    GLOBAL_XO_TUNE         = 0x0000,
                    FRR_CTL_A_MODE         = 0x0200,
                    PREAMBLE_TX_LENGTH     = 0x1000,
        )
    
#end class


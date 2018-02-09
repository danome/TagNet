from construct import *
import enum

TAGNET_VERSION = 1
DEFAULT_HOPCOUNT = 20
MAX_HOPCOUNT = 31

tagnet_message_header_s = Struct('tagnet_message_header_s',
                                 Byte('frame_length'),
                                 BitStruct('options',
                                           Flag('response'),
                                           BitField('version',3),
                                           Padding(3),
                                           Enum(BitField('tlv_payload',1),
                                                RAW               = 0,
                                                TLV_LIST          = 1,
                                                ),
                                           Enum(BitField('message_type',3),
                                                POLL              = 0,
                                                BEACON            = 1,
                                                HEAD              = 2,
                                                PUT               = 3,
                                                GET               = 4,
                                                DELETE            = 5,
                                                OPTION            = 6,
                                                ),
                                           Union('param',
                                                 BitField('hop_count',5),
                                                 Enum(BitField('error_code',5),
                                                      OK              = 0,
                                                      NO_ROUTE        = 1,
                                                      TOO_MANY_HOPS   = 2,
                                                      MTU_EXCEEDED    = 3,
                                                      UNSUPPORTED     = 4,
                                                      BAD_MESSAGE     = 5,
                                                      FAILED          = 6,
                                                      NO_MATCH        = 7,
                                                      BUSY            = 8,
                                                      ),
                                                 ),
                                           ),
                                 Byte('name_length'),
                                 )


# gps format:  '32.30642N122.61458W'
# time format: '1470998711.36'

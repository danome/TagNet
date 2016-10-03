from __future__ import print_function   # python3 print function
from builtins import *
from time import time
from datetime import datetime
from uuid import getnode as get_mac
from construct import *
import platform
from binascii import hexlify

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
                                                POST              = 3,
                                                PUT               = 4,
                                                GET               = 5,
                                                DELETE            = 6,
                                                PATCH             = 7,
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
                                                      ),
                                                 ),
                                           ),
                                 Byte('name_length'),
                                 )
from tagnames import TagName
from tagtlv import tlv_types

# there is a definition conflict of enum in tagtlv from construct, so must be in this order
#
from tagtlv import *

#------------ main message class definitions ---------------------

class TagMessage(object):
    def __init__(self, *args, **kwargs):
        """
        initialize the tagnet message  structure.
        """
        super(TagMessage,self).__init__()
        self.header = tagnet_message_header_s.parse('\x00' * tagnet_message_header_s.sizeof())
        self.name = None
        self.payload = None
        if (len(args) == 2):                                  # input is (name, [payload=]payload)
            if isinstance(args[0], TagName):
                self.name = args[0].copy()
            if (args[1]) and isinstance(args[1], TagPayload):
                self.payload = args[1].copy()
        elif (len(args) == 1):
            if isinstance(args[0], TagMessage):               # input is message
                self.name = args[0].name.copy()
                self.payload = args[0].payload.copy() if (args[0].payload) else None
            elif isinstance(args[0], TagName):                # input is name
                self.name = args[0].copy()
                self.payload = None
            elif isinstance(args[0], bytearray):              # input is bytearray
                self.parse(args[0])
        if (self.name):
            self.header.options.version = TAGNET_VERSION
            self.header.options.param.hop_count = DEFAULT_HOPCOUNT
        else:
            print('error:',args)

    def copy(self):
        """
        make an copy of this message in a new message object
        """
        msg = TagMessage(self)
        msg.header = self.header
        return msg
        
    def pkt_len(self):
        l_pl = self.payload.pkt_len() if (self.payload) else 0
        return sum([tagnet_message_header_s.sizeof(),self.name.pkt_len(),l_pl])

    def hop_count(self, n):
        self.header.options.param.hop_count = n if (n < MAX_HOPCOUNT) else DEFAULT_HOPCOUNT

    def build(self):
        """
        """            
        self.header.frame_length = (tagnet_message_header_s.sizeof() - 1) + self.name.pkt_len()
        self.header.frame_length += (self.payload.pkt_len() if (self.payload) else 0)
        self.header.name_length = self.name.pkt_len()
        self.header.options.tlv_payload = 'TLV_LIST' if (self.payload and (len(self.payload) > 1)) else 'RAW'
        l = tagnet_message_header_s.build(self.header) + self.name.build()
        l += self.payload.build() if (self.payload) else ''
        return bytearray(l)

    def parse(self, v):
        """
        """
        hdr_size = tagnet_message_header_s.sizeof()
        self.header = tagnet_message_header_s.parse(v[0:hdr_size])
        self.name = TagName(v[hdr_size:self.header.name_length+hdr_size])
        if len(v) > (hdr_size + self.header.name_length):
            self.payload = TagPayload(v[self.header.name_length+hdr_size:])
        else:
            self.payload = None

#------------ end of class definition ---------------------

class TagBeacon(TagMessage):
    def __init__(self, node_id):
        pl = TagPayload([(tlv_types.NODE_ID,node_id),
                          (tlv_types.TIME,time())])
        super(TagBeacon,self).__init__(TagName('/tag/beacon'), payload=pl)
        self.header.options.message_type = 'BEACON'
        self.header.options.param.hop_count = 1

#------------ end of class definition ---------------------

class TagGet(TagMessage):
    def __init__(self, name, pl, hop_count=None):
        super(TagGet,self).__init__(name, payload=pl)
        self.header.options.param.hop_count = hop_count if (hop_count) else 0
        self.header.options.message_type = 'GET'

#------------ end of class definition ---------------------

class TagPayload(TagTlvList):
    def __init__(self, payload=None):
        super(TagPayload,self).__init__(payload)

    def build(self):
        """
        """
        if (len(self) == 1):
            return self[0].tlv_value()
        else:
            return super(TagPayload,self).build()

#------------ end of class definition ---------------------

class TagPoll(TagMessage):
    def __init__(self, slot_time=100, slot_count=10):
        pl = TagPayload([(tlv_types.TIME,datetime.now()),
                         (tlv_types.INTEGER,slot_time),
                         (tlv_types.INTEGER,slot_count)])
        nm = TagName('/tag/poll') + TagTlv(tlv_types.NODE_ID, get_mac())     
        super(TagPoll,self).__init__(nm, pl)
        self.header.options.message_type = 'POLL'
        self.header.options.tlv_payload = 'TLV_LIST'
        self.header.options.param.hop_count = 1


#------------ end of class definition ---------------------

class TagPut(TagMessage):
    def __init__(self, name, pl, hop_count=None):
        super(TagPut,self).__init__(name, payload=pl)
        self.header.options.param.hop_count = hop_count if (hop_count) else 0
        self.header.options.message_type = 'PUT'


#------------ end of class definition ---------------------

class TagResponse(TagMessage):
    """
    note that the param field is a union that only sets hop_count, but displays all union fields.
    """
    def __init__(self, req, error_code=0, payload=None, hop_count=None):
        if (req.header.options.message_type == 'POLL') and (not payload):
            payload = TagPayload([(tlv_types.NODE_ID, get_mac()),
                                  (tlv_types.NODE_NAME, platform.node()),
                                  (tlv_types.TIME,datetime.now())])
        super(TagResponse,self).__init__(req.name, payload)
        self.header.options.message_type = req.header.options.message_type
        self.header.options.response = True
        self.header.options.param.hop_count=0       # construct doesn't handle unions right
                                          # this should be the error_code field in response
            

#------------ end of class definition ---------------------
        
class TagId(object):
    def __init__(self, id, name, gps=None):
        self.id = id
        self .name = name
        self.gps = gps
        
#------------ end of class definition ---------------------

def printmsg(msg):
    print(hexlify(msg.build()))
    print(msg.header)
    print(msg.name)
    print(msg.payload)
    
def tagmessages_test():
    tmpoll = TagPoll()
    tmrsp = TagResponse(tmpoll)
    printmsg(tmpoll)
    printmsg(tmrsp)
    txpoll = tmpoll.build()
    print(hexlify(txpoll))
    ccpoll = TagMessage(txpoll)
    xxpoll = ccpoll.build()
    hdr_size = tagnet_message_header_s.sizeof()
    print('txheader == xxheader',
          hexlify(txpoll[0:hdr_size]) == hexlify(xxpoll[0:hdr_size]),
          hexlify(txpoll[0:hdr_size]), hexlify(xxpoll[0:hdr_size]))
    return tmpoll, tmrsp, ccpoll, xxpoll


if __name__ == '__main__':
    tagmessages_test()

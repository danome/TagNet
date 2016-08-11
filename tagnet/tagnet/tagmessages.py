from time import time

from construct import *

TAGNET_VERSION = 1

tagnet_message_header_s = Struct('tagnet_message_header_s',
                                 Byte('frame_length'),
                                 BitStruct('options',
                                           Field('version',3),
                                           Padding(3),
                                           Flag('response'),
                                           Enum(BitField('tlv_payload',1),
                                                RAW               = 0,
                                                TLV_LIST          = 1,
                                                ),
                                           Enum(BitField('message_type',3),
                                                # must be non-zero value for validity checking
                                                POLL              = 1,
                                                BEACON            = 2,
                                                PUT               = 3,
                                                GET               = 4,
                                                ),
                                           Union('options',
                                                 BitField('hop_count',5),
                                                 Enum(BitField('error_code',5),
                                                      OK              = 0,
                                                      NO_ROUTE        = 1,
                                                      TOO_MANY_HOPS   = 2,
                                                      TOO_LARGE       = 3,
                                                      UNSUPPORTED     = 4,
                                                      BAD_MESSAGE     = 5,
                                                      ),
                                                 ),
                                           ),
                                 Byte('header_length'),
                                 )


#------------ main message class definitions ---------------------

class Message(object):
    def __init__(self, mtype, name, payload=None, hop_count=20):
        self.name = name # check type?
        self.payload = payload # check type?
        self.header = tagnet_message_header_s.parse('\x00' * tagnet_message_header_s.sizeof())
        self.header.options.message_type = mtype
        self.header.options.version = TAGNET_VERSION
        self.header.options.hop_count = hop_count
        super(Message,self).__init__()

    def copy(self):
        """
        make an copy of this message in a new message object
        """
        return Message(self)

        
    def pkt_len(self):
        return sum([sizeof(tagnet_message_header_s),self.name.pkt_len(),self.payload.pkt_len()])

    def build(self, v):
        """
        """
        self.header.frame_length = 4 + self.name.pkt_len() + (self.payload.pkt_len() if (self.payload) else 0)
        self.header.header_length = self.name.pkt_len()
        self.header.options.tlv_payload = 'TLV_LIST' if (self.payload and isinstance(self.payload, TagLoad))
        return tag_message_header_s.build(self.header) + self.name.build() + self.payload.build()

    def parse(self, v):
        """
        """
        return self

#------------ end of class definition ---------------------

class Poll(Message):
    def __init__(self, master_tid, time=time.time(), slot_size=10, slot_count=10):
        pl = PayLoad(Tlv(tlv_types.TIME,time.time()),
                          Tlv(tlv_types.INTEGER,slot_size),
                          Tlv(tlv_types.INTEGER,slot_count))
        super(Poll,self).__init__(TagName('POLL', '/tag/poll'), payload=pl, hop_count=1)

#------------ end of class definition ---------------------

class Beacon(Message):
    def __init__(self, node_id):
        pl = PayLoad(Tlv(tlv_types.NODE_ID,node_id),
                          Tlv(tlv_types.TIME=time.time()))
        super(Beacon,self).__init__(TagName('BEACON', '/tag/beacon'), payload=pl, hop_count=1)

#------------ end of class definition ---------------------

class Put(Message):
    def __init__(self, name, pl, hop_count=None):
        super(Put,self).__init__('PUT', name, payload=pl, hop_count)

#------------ end of class definition ---------------------

class Get(Message):
    def __init__(self, name, pl, hop_count=None):
        super(Get,self).__init__('GET', name, payload=pl, hop_count)

#------------ end of class definition ---------------------

class TagLoad(TlvList):
    def __init__(self, payload=None):
        super(Payload,self).__init__(payload)

    def copy(self):
        """
        make an exact copy of this name in a new list object
        """
        return TagLoad(self)

#------------ end of class definition ---------------------

class Response(Message):
    def __init__(self, msg):
        rsp = self.copy()
        rsp.header.options.response = True
        super(Get,self).__init__('GET', name, payload=pl, hop_count)
        

#------------ end of class definition ---------------------



#------------ helper class definitions ---------------------


class TagTLV(object):
    def __init__(self, tag, value):
        self.tag = tag
        
#------------ end of class definition ---------------------
        
class TagId(object):
    def __init__(self, id, name, gps=None):
        self.id = id
        self .name = name
        self.gps = gps
        
#------------ end of class definition ---------------------


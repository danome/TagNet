from __future__ import print_function   # python3 print function
from builtins import *
from time import time
from datetime import datetime
from uuid import getnode as get_mac
import platform
from binascii import hexlify

import copy

from tagdef import *

from tagnames import TagName

from tagtlv import tlv_types
#
# there is a definition conflict of enum in tagtlv from construct, so must
# be in this order
#
from tagtlv import *

__all__ = ['TagMessage', 'TagPoll', 'TagBeacon',
           'TagGet', 'TagPut', 'TagHead', 'TagDelete', 'TagResponse']

MAX_TAGNET_PKT_SIZE = 254


#------------ main message class definitions ---------------------

class TagMessage(object):
    """
    base class for TagNet messages

    Additional subclasses are defined for instantiating each of the message
    types as well as for the response message.
    """
    def __init__(self, *args, **kwargs):
        """
        initialize the tagnet message structure

        Messages consist of a fixed header followed by a Tag name followed by
        optional payload.

        The fixed header has:  message length,
                               protocol version,
                               request / response indicator,
                               message type,
                               hop count / error code,
                               name length

        Names consist of a list of tag tlvs that represent the hierachical order
        of name components that make up the identifier for a named data object.

        Payloads can consist of either a list of tlvs or a byte array (flag
        in header specifies which one).

        Note this class is intended to be subclassed as a set of classes for the
        message type and payload specifics of the various protocol message types.
        """
        super(TagMessage,self).__init__()
        self.header = tagnet_message_header_s.parse('\x00'
                                                * tagnet_message_header_s.sizeof())
        self.name = None
        self.payload = None
        if (len(args) == 2):                   # input is (name [, payload])
            if isinstance(args[0], TagName):
                self.name = args[0].copy()
            else:
                raise TypeError('too few/many arguments')
            if (args[1]) and isinstance(args[1], TagTlvList):
                self.payload = args[1].copy()
            elif (args[1]) and isinstance(args[1], bytearray):
                self.payload = args[1]
            else:
                raise TypeError('bad payload type')
        elif (len(args) == 1):
            if isinstance(args[0], TagMessage):               # input is message
                self.name = args[0].name.copy()
                if (args[0].payload) and isinstance(args[0].payload, TagTlvList):
                    self.payload = args[0].payload.copy()
                elif (args[0].payload) and isinstance(args[0].payload, bytearray):
                    self.payload = args[0].payload
                else:
                    raise TypeError('bad payload type')
            elif isinstance(args[0], TagName):                # input is name
                self.name = args[0].copy()
            elif isinstance(args[0], bytearray):              # input is bytearray
                self.parse(args[0])
            else:
                raise TypeError('bad input type: {}, value:'.format(type(args[0]), hexlify(args[0])))
        else:
            raise ValueError('too few/many arguments')
        self.header.frame_length = tagnet_message_header_s.sizeof() - 1
        if (self.name):
            self.header.name_length = self.name.pkt_len()
            self.header.frame_length += self.header.name_length
            self.header.options.version = TAGNET_VERSION
            if (self.payload) and (isinstance(self.payload, TagTlvList)):
                self.header.options.tlv_payload = 'TLV_LIST'
                self.header.frame_length += self.payload.pkt_len()
            elif (self.payload) and (isinstance(self.payload, bytearray)):
                self.header.options.tlv_payload = 'RAW'
                self.header.frame_length += len(self.payload)
            elif (self.payload):
                raise TypeError('bad payload type')
        else:
            print('error in constructing tag message:',args)

    def copy(self):
        """
        make a copy of this message in a new message object
        """
        msg = TagMessage(self)
        msg.header = copy.copy(self.header)
        return msg

    def pkt_len(self):
        """
        return the length of the packet (on the wire)

        Note that value may change if message is further modified.
        """
        l_pl = 0
        if (self.payload):
            if isinstance(self.payload, TagTlvList):  l_pl = self.payload.pkt_len()
            elif isinstance(self.payload, bytearray): l_pl = len(self.payload)
        return sum([tagnet_message_header_s.sizeof(),self.name.pkt_len(),l_pl])

    def payload_avail(self):
        used_bytes = self.pkt_len()
        free_bytes = (MAX_TAGNET_PKT_SIZE - used_bytes) \
                     if (used_bytes < MAX_TAGNET_PKT_SIZE) else 0
        return free_bytes

    def hop_count(self, n=None):
        """
        get/set hop count in message

        """
        x = self.header.options.param.hop_count
        if (n):
            if (n == -1):
                self.header.options.param.hop_count = DEFAULT_HOPCOUNT
            else:
                self.header.options.param.hop_count = n if (n <= MAX_HOPCOUNT) else DEFAULT_HOPCOUNT
        return x

    def build(self):
        """
        construct the wire format byte string of the message
        """
        if (self.payload):
            if isinstance(self.payload, TagTlvList):  l_pl = self.payload.pkt_len()
            elif isinstance(self.payload, bytearray): l_pl = len(self.payload)
        else:                                         l_pl = 0
        self.header.frame_length = (tagnet_message_header_s.sizeof() - 1) \
                                   + self.name.pkt_len() \
                                   + l_pl
        self.header.name_length = self.name.pkt_len()
        self.header.options.tlv_payload = \
                        'TLV_LIST' if (self.payload and isinstance(self.payload, TagTlvList)) \
                        else 'RAW'
        l = tagnet_message_header_s.build(self.header) + self.name.build()
        if (self.payload):
            if isinstance(self.payload, TagTlvList):  l += self.payload.build()
            elif isinstance(self.payload, bytearray): l += self.payload
        return bytearray(l)

    def parse(self, v):
        """
        deconstruct a wire formated byte string into the message class
        """
        hdr_size = tagnet_message_header_s.sizeof()
        self.header = tagnet_message_header_s.parse(v[0:hdr_size])
        self.name = TagName(v[hdr_size:self.header.name_length+hdr_size])
        if len(v) > (hdr_size + self.header.name_length):
            if (self.header.options.tlv_payload == 'TLV_LIST'):
                self.payload = TagTlvList(v[self.header.name_length+hdr_size:])
            else:
                self.payload = bytearray(v[self.header.name_length+hdr_size:])
        else:
            self.payload = None

#------------ end of class definition ---------------------

class TagBeacon(TagMessage):
    """
    instantiate a Tagnet Beacon message

    Put node_id and datetime in the payload.
    """
    def __init__(self, node_id=None):
        if (not node_id): node_id = get_mac()
        pl = TagTlvList([(tlv_types.NODE_ID,node_id),
                         (tlv_types.NODE_NAME, platform.node()),
                         (tlv_types.TIME,datetime.now())])
        nm = TagName('/tag/beacon') + TagTlv(tlv_types.NODE_ID, -1)
        super(TagBeacon,self).__init__(nm, pl)
        self.header.options.message_type = 'BEACON'
        self.hop_count(1)   # never forward this message

#------------ end of class definition ---------------------

class TagGet(TagMessage):
    """
    instantiate a TagNet Get message
    """
    def __init__(self, name, pl=None, hop_count=None):
        if (pl):
            super(TagGet,self).__init__(name, pl)
        else:
            super(TagGet,self).__init__(name)
        self.header.options.message_type = 'GET'
        if (hop_count):
            self.hop_count(hop_count)
        else:
            self.hop_count(DEFAULT_HOPCOUNT)

#------------ end of class definition ---------------------

class TagHead(TagMessage):
    """
    Instantiate a TagNet Put message
    """
    def __init__(self, name, pl=None, hop_count=None):
        if (pl):
            super(TagHead,self).__init__(name, pl)
        else:
            super(TagHead,self).__init__(name)
        self.header.options.message_type = 'HEAD'
        if (hop_count):
            self.hop_count(hop_count)
        else:
            self.hop_count(DEFAULT_HOPCOUNT)

#------------ end of class definition ---------------------

class TagPoll(TagMessage):
    """
    Instantiate a TagNet Poll message

    Add time-of-day, slot_time, slot_count to payload
    """
    def __init__(self, slot_time=100, slot_count=10):
        nm = TagName([TagTlv(tlv_types.NODE_ID, -1),
                      TagTlv('tag'),
                      TagTlv('poll'),
                      TagTlv('ev')])
        pl = TagTlvList([
            #(tlv_types.TIME,datetime.now()),
            (tlv_types.INTEGER,slot_time),
            (tlv_types.INTEGER,slot_count),
            (tlv_types.NODE_ID, get_mac()),
            (tlv_types.NODE_NAME, platform.node()),
        ])
        super(TagPoll,self).__init__(nm, pl)
        self.header.options.message_type = 'POLL'
        self.hop_count(1)   # never forward this message

#------------ end of class definition ---------------------

class TagPut(TagMessage):
    """
    Instantiate a TagNet Put message
    """
    def __init__(self, name, pl=None, hop_count=None):
        if (pl):
            super(TagPut,self).__init__(name, pl)
        else:
            super(TagPut,self).__init__(name)
        self.header.options.message_type = 'PUT'
        if (hop_count):
            self.hop_count(hop_count)
        else:
            self.hop_count(DEFAULT_HOPCOUNT)

#------------ end of class definition ---------------------

class TagDelete(TagMessage):
    """
    Instantiate a TagNet Delete message
    """
    def __init__(self, name, pl=None, hop_count=None):
        if (pl):
            super(TagDelete,self).__init__(name, pl)
        else:
            super(TagDelete,self).__init__(name)
        self.header.options.message_type = 'DELETE'
        if (hop_count):
            self.hop_count(hop_count)
        else:
            self.hop_count(DEFAULT_HOPCOUNT)

#------------ end of class definition ---------------------

class TagResponse(TagMessage):
    """
    set message to response

    Uses existing request message name and sets header fields for
    response.

    If responding to a Poll request, return payload with: node id, node
    name, and time-of-day.
    Note that the param field is a union that only sets hop_count, but
    displays all union fields.
    """
    def __init__(self, req, error_code=0, payload=None):
        if (req.header.options.message_type == 'POLL') and (not payload):
            payload = TagTlvList([(tlv_types.NODE_ID, get_mac()),
                                  (tlv_types.NODE_NAME, platform.node()),
                                  (tlv_types.TIME,datetime.now())])
        super(TagResponse,self).__init__(req.name, payload)
        self.header.options.message_type = req.header.options.message_type
        self.header.options.response = True
        # construct doesn't handle unions properly
        # this is setting the error_code field in response
        self.header.options.param.hop_count=error_code

#------------ end of class definition ---------------------

class TagId(object):
    """
    """
    def __init__(self, id, name, gps=None):
        self.id = id
        self.name = name
        self.gps = gps

#------------ end of class definition ---------------------

def printmsg(msg):
    print(hexlify(msg.build()))
    print(msg.header)
    print(msg.name)
    if msg.header.options.tlv_payload == 'TLV_LIST':
        print(msg.payload)
    else:
        print(hexlify(msg.payload))
def tagmessages_test():
    tmpoll = TagPoll()
    tmrsp = TagResponse(tmpoll)
    printmsg(tmpoll)
    printmsg(tmrsp)

    txpoll = tmpoll.build()
    cmpoll = TagMessage(txpoll)
    printmsg(cmpoll)
    cxpoll = cmpoll.build()
    print('tx',hexlify(txpoll))
    print('cx',hexlify(cxpoll))

    hdr_size = tagnet_message_header_s.sizeof()
    print('txheader == xxheader',
          hexlify(txpoll[0:hdr_size]) == hexlify(cxpoll[0:hdr_size]),
          hexlify(txpoll[0:hdr_size]), hexlify(cxpoll[0:hdr_size]))

    tmbeacon = TagBeacon()
    printmsg(tmbeacon)
    nm = TagName('/tag/info/') + TagTlv(tlv_types.NODE_ID, -1)\
         + TagName('/sens/gps/pos')
#         + TagTlv('sensor') + TagTlv('gps') + TagTlv('fix')
    pl = TagTlvList([(tlv_types.INTEGER,123456789),])
    tmput = TagPut(nm,pl)
    printmsg(tmput)
    tbput = TagPut(nm,bytearray(b'abc'))
    printmsg(tbput)

    return tmpoll, txpoll, tmrsp, cmpoll, cxpoll, tmput, tbput


if __name__ == '__main__':
    tagmessages_test()

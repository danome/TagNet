from __future__ import print_function   # python3 print function
from builtins import *
from time import time
from datetime import datetime
from uuid import getnode as get_mac
import platform
from binascii import hexlify

import copy

from tagdef import *
import construct

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

# http://www.sunshine2k.de/coding/javascript/crc/crc_js.html
# https://gist.github.com/hypebeast/3833758

class crc8:
    def __init__(self):
        self.crcTable = (0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15, 0x38,
                         0x3f, 0x36, 0x31, 0x24, 0x23, 0x2a, 0x2d, 0x70, 0x77,
                         0x7e, 0x79, 0x6c, 0x6b, 0x62, 0x65, 0x48, 0x4f, 0x46,
                         0x41, 0x54, 0x53, 0x5a, 0x5d, 0xe0, 0xe7, 0xee, 0xe9,
                         0xfc, 0xfb, 0xf2, 0xf5, 0xd8, 0xdf, 0xd6, 0xd1, 0xc4,
                         0xc3, 0xca, 0xcd, 0x90, 0x97, 0x9e, 0x99, 0x8c, 0x8b,
                         0x82, 0x85, 0xa8, 0xaf, 0xa6, 0xa1, 0xb4, 0xb3, 0xba,
                         0xbd, 0xc7, 0xc0, 0xc9, 0xce, 0xdb, 0xdc, 0xd5, 0xd2,
                         0xff, 0xf8, 0xf1, 0xf6, 0xe3, 0xe4, 0xed, 0xea, 0xb7,
                         0xb0, 0xb9, 0xbe, 0xab, 0xac, 0xa5, 0xa2, 0x8f, 0x88,
                         0x81, 0x86, 0x93, 0x94, 0x9d, 0x9a, 0x27, 0x20, 0x29,
                         0x2e, 0x3b, 0x3c, 0x35, 0x32, 0x1f, 0x18, 0x11, 0x16,
                         0x03, 0x04, 0x0d, 0x0a, 0x57, 0x50, 0x59, 0x5e, 0x4b,
                         0x4c, 0x45, 0x42, 0x6f, 0x68, 0x61, 0x66, 0x73, 0x74,
                         0x7d, 0x7a, 0x89, 0x8e, 0x87, 0x80, 0x95, 0x92, 0x9b,
                         0x9c, 0xb1, 0xb6, 0xbf, 0xb8, 0xad, 0xaa, 0xa3, 0xa4,
                         0xf9, 0xfe, 0xf7, 0xf0, 0xe5, 0xe2, 0xeb, 0xec, 0xc1,
                         0xc6, 0xcf, 0xc8, 0xdd, 0xda, 0xd3, 0xd4, 0x69, 0x6e,
                         0x67, 0x60, 0x75, 0x72, 0x7b, 0x7c, 0x51, 0x56, 0x5f,
                         0x58, 0x4d, 0x4a, 0x43, 0x44, 0x19, 0x1e, 0x17, 0x10,
                         0x05, 0x02, 0x0b, 0x0c, 0x21, 0x26, 0x2f, 0x28, 0x3d,
                         0x3a, 0x33, 0x34, 0x4e, 0x49, 0x40, 0x47, 0x52, 0x55,
                         0x5c, 0x5b, 0x76, 0x71, 0x78, 0x7f, 0x6a, 0x6d, 0x64,
                         0x63, 0x3e, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2c, 0x2b,
                         0x06, 0x01, 0x08, 0x0f, 0x1a, 0x1d, 0x14, 0x13, 0xae,
                         0xa9, 0xa0, 0xa7, 0xb2, 0xb5, 0xbc, 0xbb, 0x96, 0x91,
                         0x98, 0x9f, 0x8a, 0x8d, 0x84, 0x83, 0xde, 0xd9, 0xd0,
                         0xd7, 0xc2, 0xc5, 0xcc, 0xcb, 0xe6, 0xe1, 0xe8, 0xef,
                         0xfa, 0xfd, 0xf4, 0xf3)
    def crc(self, msg):
        runningCRC = 0
        for c in msg:
            #c = ord(str(c))
            runningCRC = self.crcByte(runningCRC, c)
        # zzz print('crc', hex(runningCRC), len(msg), hexlify(msg))
        return runningCRC
    def crcByte(self, oldCrc, byte):
        res = self.crcTable[oldCrc & 0xFF ^ byte & 0xFF]
        return res


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
        self.crc8 = crc8()
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
        if (self.name):
            self.header.frame_length = tagnet_message_header_s.sizeof() - 1
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
            raise ValueError('error in constructing tag message:',args)

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
        # +1 for crc implied from sizeof header not decreasing for length field
        self.header.frame_length = (tagnet_message_header_s.sizeof()) \
                                   + self.name.pkt_len() \
                                   + l_pl
        self.header.name_length = self.name.pkt_len()
        self.header.options.tlv_payload = \
                        'TLV_LIST' if (self.payload and isinstance(self.payload, TagTlvList)) \
                        else 'RAW'
        msg = tagnet_message_header_s.build(self.header) + self.name.build()
        if (self.payload):
            if isinstance(self.payload, TagTlvList):  msg += self.payload.build()
            elif isinstance(self.payload, bytearray): msg += self.payload
        # add crc8
        msg.append(self.crc8.crc(msg))
        return bytearray(msg)

    def parse(self, v):
        """
        deconstruct a wire formated byte string into the message class
        """
        # verify crc8
        if (self.crc8.crc(v[:-1]) == v[-1]):
            hdr_size = tagnet_message_header_s.sizeof()
            try:
                self.header = tagnet_message_header_s.parse(v[0:hdr_size])
                self.name = TagName(v[hdr_size:self.header.name_length+hdr_size])
                if len(v) > (hdr_size + self.header.name_length):
                    if (self.header.options.tlv_payload == 'TLV_LIST'):
                        self.payload = TagTlvList(v[self.header.name_length+hdr_size:-1])
                    else:
                        self.payload = bytearray(v[self.header.name_length+hdr_size:-1])
                else:
                    self.payload = None
            except (construct.adapters.MappingError, TlvBadException, TlvListBadException):
                self.header  = None
                self.name    = None
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
    def __init__(self, slot_width=1000, slot_count=10):
        nm = TagName([TagTlv(tlv_types.NODE_ID, -1),
                      TagTlv('tag'),
                      TagTlv('poll'),
                      TagTlv('ev')])
        pl = TagTlvList([
            (tlv_types.NODE_ID, get_mac()),
            (tlv_types.NODE_NAME, platform.node()),
            (tlv_types.INTEGER,slot_width),
            (tlv_types.INTEGER,slot_count),
            #(tlv_types.TIME,datetime.now()),
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

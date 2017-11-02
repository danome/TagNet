from __future__ import print_function   # python3 print function
from builtins import *                  # python3 types
import os, sys, types
from os.path import normpath, commonprefix
from temporenc import packb, unpackb
from binascii import hexlify
from struct import pack, unpack

from tagdef import *

def _forever(v):
    """
    Returns the same value it is instantiated with each time it is called using .next()
    """
    while True:
        yield (v)


class TagTlvList(list):
    """
    constructor for Tag TLV lists.

    Used for specifying tag names and payloads.
    """
    zstring=_forever(tlv_types.STRING)

    def __init__(self, *args, **kwargs):
        """
        initialize the tlv list structure

        Expects a single parameter of one of the following types:
        - String
        - bytearray
        - TagTlvList
        - list of TagTlvs [tlv, ...]
        - list of tuples [(type, value)...]

        Make sure that all elements added are valid tlv_types.
        """
        super(TagTlvList,self).__init__()
        if (len(args) == 1):
            if isinstance(args[0], types.StringType):
                for t,v in (zip(self.zstring,normpath(args[0]).split(os.sep)[1:])):
                    self.append(TagTlv(t,v))
                return
            elif isinstance(args[0], TagTlvList):
                for tlv in args[0]:
                    self.append(TagTlv(tlv))
                return
            elif isinstance(args[0], bytearray):
                self.parse(args[0])
                return
            else: # isinstance(args[0], types.ListType)
                if isinstance(args[0][0], types.TupleType):
                    for t,v in args[0]:
                        self.append(TagTlv(t,v))
                    return
                elif isinstance(args[0][0], TagTlv):
                    for tlv in args[0]:
                        self.append(TagTlv(tlv))
                    return
        print('error:', args, type(args[0][0]) if (args and args[0]) else '')

    #------------ following methods extend base class  ---------------------

    def build(self):
        """
        construct the packet formatted string from tagtlvlist
        """
        fb = bytearray(b'')
        for tlv in self:
            fb += tlv.build()
        return fb

    def copy(self):
        """
        make a copy of this tlvlist in a new tlvlist object
        """
        return TagTlvList(self)

    def endswith(self, d):
        """
        """
        return self

    def parse(self, v):
        """
        process packet formatted string of tlvs into a tagtlvlist. replaces current list
        """
        x = 0
        while (x < len(v)):
            y = v[x+1] + 2
            self.append(TagTlv(v[x:x+y]))
            x += y

    def pkt_len(self):  # needs fixup
        """
        sum up the sizes of each tlv based on packet space required
        """
        return sum([len(tlv) for tlv in self])

    def startswith(self, d):
        """
        check to see if this name begins withs with specified name. True if prefix matches exactly.
        """
        return True if (os.path.commonprefix([self,d]) == d) else False


    #------------ following methods overload base class  ---------------------

    def append(self, o):
        """
        append overloaded to handle possible format conversions of value in appending object
        """
        return self.extend([o])

    def extend(self, l):
        """
        extend overloaded to handle possible format conversions of value in extending list
        """
        tl = []
        for o in l:
            tl.append(TagTlv(o))
        super(TagTlvList,self).extend(tl)
        return self

    def insert(self, i, o):
        """
        insert overloaded to handle possible format conversions of value in inserting object
        """
        return super(TagTlvList,self).insert(i,TagTlv(o))

    def __add__(self,o):
        """
        __add__ overloaded to handle possible format conversions of value in adding object
        """
        l = o if isinstance(o, list) else [o]
        return self.extend(l)

#------------ end of class definition ---------------------


class TagTlv(object):
    """
    Constructor for a TagNet Type-Length-Value (TLV) Objects

    Handles the translation between network format and python structures.
    """
    def __init__(self, t, v=None):
        """
        initialize the specified TLV type with optional value

        The value can be of various formats, including:
          TagTlv, bytearray, Integer, Long, String, or Tuple(T,V)

        The bytearray is interpreted to be network formated data.
        The Tuple consists of a TagTlv Type and a bytearray for Value.
        """
        self.tuple = None
        if (v is not None):
            self._convert(t,v)
        elif isinstance(t, TagTlv):
            self.tuple = t.tuple
        elif isinstance(t, bytearray):
            self.parse(t)
        elif isinstance(t, types.IntType) or isinstance(t, types.LongType):
            self._convert(tlv_types.INTEGER, t)
        elif isinstance(t, types.StringType):
            self._convert(tlv_types.STRING, t)
        elif isinstance(t, types.TupleType):
            self._convert(t[0],t[1])
        elif isinstance(t, type(tlv_types.EOF)):
            self._convert(t, '')
        else:
            print("bad tlv init", t, v)


    def _convert(self, t, v):
        """
        convert a network formated type-value into object instance
        """
        if (t is tlv_types.STRING) or (t is tlv_types.NODE_NAME):
            if isinstance(v, types.StringType) or isinstance(v, bytearray):
                self.tuple = (t, str(v))
        elif (t is tlv_types.INTEGER) or (t is tlv_types.OFFSET):
            if  isinstance(v, types.IntType) or isinstance(v, types.LongType):
                self.tuple =  (t, int(v))
            else:
                self.tuple = (t, 0)
        elif t is tlv_types.GPS:
            # zzz
            v = bytearray.fromhex(''.join('%02X' % (v[i]) for i in xrange(12)))
#            v = bytearray.fromhex(''.join('%02X' % (v[i]) for i in reversed(xrange(12))))
            self.tuple =  (t, v)
        elif t is tlv_types.TIME:
            self.tuple =  (t, v)
        elif t is tlv_types.NODE_ID:
            if isinstance(v, types.IntType) or isinstance(v, types.LongType):
                v = bytearray.fromhex(
                    ''.join('%02X' % ((v >> 8*i) & 0xff) for i in xrange(6)))
#                    ''.join('%02X' % ((v >> 8*i) & 0xff) for i in reversed(xrange(6))))
            elif isinstance(v, types.StringType):
                v = bytearray.fromhex(v)
            self.tuple =  (t, bytearray(v))
        elif t is tlv_types.VERSION:
            if isinstance(v, list) or isinstance(v, tuple):
                v = pack('HBB', *v)
            self.tuple = (t, v)
        elif t is tlv_types.EOF:
            self.tuple = (t, '')
        else:
            print("bad tlv convert", t, v)

    def update(self, t, v=None):
        """
        modify existing type and value fields of object
        """
        if (v is None):
            if isinstance(t, TagTlv):
                self._convert(t.tlv_type(),t.value())
            elif isinstance(t, types.TupleType):
                self._convert(t[0],t[1])
            elif isinstance(t, bytearray):
                self.parse(t)
        else:
            self._convert(t, v)
        if (not self.tuple):
            print('error tlv ({}): {} / {}'.format(type(t), t, v))

    def int_to_tlv_type(self, i):
        for tlvt in tlv_types:
            if (tlvt.value == i): return tlvt
        return None

    def parse(self, fb):
        """
        parse packet formatted tlv into object instance
        """
        t = self.int_to_tlv_type(fb[0])
        l = fb[1]
        v = bytearray(fb[2:])
        if (l != len(v)):
            print('tlv bad parse: {}'.format(fb))
        if t is tlv_types.TIME:
             v = unpackb(v).datetime()
        elif  (t is tlv_types.INTEGER) or (t is tlv_types.OFFSET):
#            print(t,l,hexlify(v))
            a = 0
            for i in range(l): a = (a << 8) + v[i]
            v = a
#            for i in range(l): a = (a * 256) + int.from_bytes(v[i],'big')
#            v = int.from_bytes(v, 'big')
        elif t is tlv_types.NODE_ID or t is tlv_types.GPS:
            v = bytearray(v)
        elif t is tlv_types.VERSION:
            v = bytearray(v)
        elif t is tlv_types.EOF:
            v = bytearray()
        self._convert(t, v)

    def build(self):
        """
        build a packet formatted tlv from object instance
        """
        t = self.tlv_type()
        if (t is tlv_types.STRING):
            v = self.value().encode()
        elif (t is tlv_types.NODE_NAME):
            v = self.value().encode()
        elif (t is tlv_types.INTEGER) or (t is tlv_types.OFFSET):
            n = int(self.value())
            p = pack('>L', n)
            for i in range(0,4):
                if (p[i] != '\x00'): break
            v = p[i:]
#            v = n.to_bytes((len(hex(n)[2:])+1)/2,'big', signed=True)
        elif t is tlv_types.GPS:
            # zzz
            v = self.value().encode()
        elif t is tlv_types.TIME:
            v = packb(self.value())
        elif t is tlv_types.NODE_ID:
            v = self.value()
        elif t is tlv_types.VERSION:
            v = self.value()
        elif t is tlv_types.EOF:
            v = ''
        h = int(t.value).to_bytes(1,'big') + int(len(v)).to_bytes(1,'big')
        return h + v

    def tlv_type(self):
        return self.tuple[0]

    def value(self):
        return self.tuple[1]

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        # zzz
        if (self.tlv_type() is tlv_types.NODE_ID)\
                 or (self.tlv_type() is tlv_types.GPS):
            v = hexlify(self.value())
        elif (self.tlv_type() is tlv_types.VERSION):
            v = list(unpack('HBB', self.value()))
        elif (self.tlv_type() is tlv_types.EOF):
            v = ''
        else:
            v = self.value()
        return '({}, {})'.format(self.tlv_type(),v)

    def __len__(self):
        l = 0
        t = self.tlv_type()
        if (t is tlv_types.STRING) or (t is tlv_types.NODE_NAME):
            l = len(self.value())
        elif (t is tlv_types.INTEGER) or (t is tlv_types.OFFSET):
            l = (len(hex(self.value())[2:])+1)/2
        elif t is tlv_types.GPS:
            l = len(self.value())
        elif t is tlv_types.TIME:
            l = len(packb(self.value()))
        elif t is tlv_types.NODE_ID:
            l = len(self.value())
        elif t is tlv_types.VERSION:
            l = len(self.value())
        elif t is tlv_types.EOF:
            l = len(self.value())
        return l + 2

#------------ end of class definition ---------------------

def test_tlv():
    # tagtlv.__init__()
    #   tuple
    tstr = TagTlv(tlv_types.STRING,'abc')
    tint1 = TagTlv(tlv_types.INTEGER, 1)
    tint10k = TagTlv(tlv_types.INTEGER, 10000)
    from datetime import datetime
    ttime = TagTlv(tlv_types.TIME, datetime.now())
    from uuid import getnode as get_mac
    tnid1 = TagTlv(tlv_types.NODE_ID, get_mac())
    tnid2 = TagTlv(tlv_types.NODE_ID, ''.join('%02X' % ((get_mac() >> 8*i) & 0xff) for i in reversed(xrange(6))))
    import platform
    tnn =  TagTlv(tlv_types.NODE_NAME, platform.node())
    #   tagtlv
    ttlv = TagTlv(tstr)
    #   bytearray
    tba = TagTlv(bytearray.fromhex(b'0103746167'))
    # build()
    ostr = tstr.build()
    oint1 = tint1.build()
    oint10k = tint10k.build()
    otlv = ttlv.build()
    oba = tba.build()
    otime = ttime.build()
    onid1 = tnid1.build()
    onid2 = tnid2.build()
    onn = tnn.build()
    # parse()
    tstr.parse(ostr)
    tint1.parse(oint1)
    tint10k.parse(oint10k)
    ttlv.parse(otlv)
    tba.parse(oba)
    ttime.parse(otime)
    tnid1.parse(onid1)
    tnid2.parse(onid2)
    tnn.parse(onn)
    # len()
    print('tstr', len(tstr), tstr, tstr.tlv_type(), tstr.value(), hexlify(ostr))
    print('tint1', len(tint1), tint1, tint1.tlv_type(), tint1.value(), hexlify(oint1))
    print('tint10k', len(tint10k), tint10k, tint10k.tlv_type(), tint10k.value(), hexlify(oint10k))
    print('ttlv', len(ttlv), ttlv, ttlv.tlv_type(), ttlv.value(), hexlify(otlv))
    print('tba', len(tba), tba, tba.tlv_type(), tba.value(), hexlify(oba))
    print('ttime', len(ttime), ttime, ttime.tlv_type(), ttime.value(), hexlify(otime))
    print('tnid1', len(tnid1), tnid1, tnid1.tlv_type(), hexlify(tnid1.value()), hexlify(onid1))
    print('tnid2', len(tnid2), tnid2, tnid2.tlv_type(), hexlify(tnid2.value()), hexlify(onid2))
    print('tnn', len(tnn), tnn, tnn.tlv_type(), tnn.value(), hexlify(onn))
    # == succeeds
    print('tstr==ttlv', tstr == ttlv)
    print('tnid1==tnid2', tnid1 == tnid2)
    # == fails
    print('tstr==tint1', tstr == tint1)
    return tstr,tint1,tint10k,ttlv,tba,ttime,tnid1,tnid2,tnn,ostr,oint1,oint10k,otlv,oba,otime,onid1,onid2,onn

def test_tlv_list():
    # tagtlvlist.__init__()
    #    stringtype
    tlstr = TagTlvList('/foo/bar')
    #    tagtlvlist
    tllist = TagTlvList(tlstr)
    #    bytearray
    tlba = TagTlvList(bytearray.fromhex(b'01037461670104706f6c6c'))
    #    list of tuples
    tltups = TagTlvList([(tlv_types.STRING, 'baz'),(tlv_types.STRING,'zob')])
    #    list of tagtlvs
    tltlvs = TagTlvList([TagTlv(tlv_types.STRING,'abc'),TagTlv(tlv_types.INTEGER, 1)])
    # build()
    olstr = tlstr.build()
    ollist = tllist.build()
    oltlvs = tltlvs.build()
    oltups = tltups.build()
    olba = tlba.build()
    # parse()
    tlstr.parse(olstr)
    tllist.parse(ollist)
    tltlvs.parse(oltlvs)
    tltups.parse(oltups)
    tlba.parse(olba)
    # endswith()
    # pkt_len()
    print('tlstr', len(tlstr), tlstr.pkt_len(), tlstr, hexlify(olstr))
    print('tllist', len(tllist), tllist.pkt_len(), tllist, hexlify(ollist))
    print('tltlvs', len(tltlvs), tltlvs.pkt_len(), tltlvs, hexlify(oltlvs))
    print('tltups', len(tltups), tltups.pkt_len(), tltups, hexlify(oltups))
    print('tlba', len(tlba), tlba.pkt_len(), tlba, hexlify(olba))
    # startswith()
    print('startswith', tllist, tlstr, tllist.startswith(tlstr))
    print('startswith', tlstr, tllist, tlstr.startswith(tllist))
    # append()
    a = TagTlvList('')
    print('append', a, 'string baz', a.append((tlv_types.STRING, 'baz')))
    # extend()
    print('extend', a, tlba, a.extend(tlba))
    # insert()
    print('insert')
    # __add__()
    print('add')
    print(olstr)
    return tlstr,tllist,tltups,tltlvs,tlba,olstr

def tagtlv_test():
    test_tlv()
    test_tlv_list()

if __name__ == '__main__':
    tagtlv_test()

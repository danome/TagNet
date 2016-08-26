import os, sys, types
from os.path import normpath, commonprefix
import binascii
from temporenc import packb, unpackb

#from enum import Enum, unique
import enum

@enum.unique
class tlv_types(enum.Enum):
    STRING                 =  1
    INTEGER                =  2
    GPS                    =  3
    TIME                   =  4
    NODE_ID                =  5
    NODE_NAME              =  6

from tagdef import *

# gps format:  '32.30642N122.61458W'
# time format: '1470998711.36'

def _forever(v):
    """
    Returns the same value it is instantiated with each time it is called using .next()
    """
    while True:
        yield (v)


class TagTlvList(list):
    """
    constructor for tag names, which consist of a list of tag tlv's that represent the hierachical order of
    name components as defined by the list.
    """
    zstring=_forever(tlv_types.STRING)

    def __init__(self, *args, **kwargs):
        """
        initialize the tlv list structure. make sure that all elements added are valid tlv_types.
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
    def __init__(self, t, v=None):
        self.tuple = None
        if (v):
            self._convert(t,v)
        elif isinstance(t, TagTlv):
            self.tuple = t.tuple
        elif isinstance(t, bytearray):
            self.parse(t)
        elif isinstance(t, types.TupleType):
            self._convert(t[0],t[1])
        else:
            print "bad tlv init", t, v
    

    def _convert(self, t, v):
        """
        convert external input value into object storage representation
        """
        if (t is tlv_types.STRING) or (t is tlv_types.NODE_NAME):
            if isinstance(v, types.StringType) or isinstance(v, bytearray):
                self.tuple = (t, str(v))
        elif t is tlv_types.INTEGER:
            if  isinstance(v, types.IntType) or isinstance(v, bytearray):
                self.tuple =  (t, int(v))
        elif t is tlv_types.GPS:
            self.tuple =  (t, bytearray(str(v)))
        elif t is tlv_types.TIME:
            self.tuple =  (t, v)
        elif t is tlv_types.NODE_ID:
            if isinstance(v, types.IntType):
                v = hex(v)[2:].decode('hex')
            self.tuple =  (t, v)
        else:
            print "bad tlv convert", t, v
      
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
        v = fb[2:]
        if (l != len(v)):
            print('tlv bad parse: {}'.format(fb))
        if (t == tlv_types.TIME):
             v = unpackb(v).datetime()
        self._convert(t, v)

    def build(self):
        """
        build a packet formatted tlv from object instance
        """
        h = bytearray()
        v = bytearray()
        t = self.tlv_type()
        if (t is tlv_types.STRING) or (t is tlv_types.NODE_NAME):
            v.extend(self.value())
        elif t is tlv_types.INTEGER:
            v.append(self.value())
        elif t is tlv_types.GPS:
            v.extend(self.value())
        elif t is tlv_types.TIME:
            v.extend(packb(self.value()))
        elif t is tlv_types.NODE_ID:
            v.extend(self.value())
        h.extend([t.value, len(v)])
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
        v = self.value().encode('hex') if self.tlv_type() is tlv_types.NODE_ID else self.value()
        return '({}, {})'.format(self.tlv_type(),v)

    def __len__(self):
        l = 0
        t = self.tlv_type()
        if (t is tlv_types.STRING) or (t is tlv_types.NODE_NAME):
            l = len(self.value())
        elif t is tlv_types.INTEGER:
            l = len(bytearray(hex(self.value())))
        elif t is tlv_types.GPS:
            l = len(self.value())
        elif t is tlv_types.TIME:
            l = len(packb(self.value()))
        elif t is tlv_types.NODE_ID:
            l = len(self.value())
        return l + 2

#------------ end of class definition ---------------------

def test_tlv():
    # tagtlv.__init__()
    #   tuple
    tstr = TagTlv(tlv_types.STRING,'abc')
    tint = TagTlv(tlv_types.INTEGER, 1)
    #   tagtlv
    ttlv = TagTlv(tstr)
    #   bytearray
    tba = TagTlv(bytearray.fromhex(b'0103746167'))
    # build()
    o1 = tba.build()
    # parse()
    tstr.parse(o1)
    # len()
    print 'tstr', len(tstr), tstr
    print 'tint', len(tint), tint
    print 'ttlv', len(ttlv), ttlv
    print 'tba', len(tba), tba
    # == succeeds
    print 'tstr==tba', tstr == tba
    # == fails
    print 'tstr==tint', tstr == tint
    print o1
    return tstr,tint,ttlv,tba,o1

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
    ol1 = tlstr.build()
    # parse()
    tlstr.parse(ol1)
    # endswith()
    # pkt_len()
    print 'tlstr', len(tlstr), tlstr.pkt_len(), tlstr
    print 'tllist', len(tllist), tllist.pkt_len(), tllist
    print 'tltlvs', len(tltlvs), tltlvs.pkt_len(), tltlvs
    print 'tltups', len(tltups), tltups.pkt_len(), tltups
    print 'tlba', len(tlba), tlba.pkt_len(), tlba
    # startswith()
    print 'startswith', tllist, tlstr, tllist.startswith(tlstr)
    print 'startswith', tlstr, tllist, tlstr.startswith(tllist)
    # append()
    a = TagTlvList('')
    print 'append', a, 'string baz', a.append((tlv_types.STRING, 'baz'))
    # extend()
    print 'extend', a, tlba, a.extend(tlba)
    # insert()
    print 'insert'
    # __add__()
    print 'add'
    print ol1
    return tlstr,tllist,tltups,tltlvs,tlba,ol1

def tagtlv_test():
    test_tlv()
    test_tlv_list()
    
if __name__ == '__main__':
    tagtlv_test()


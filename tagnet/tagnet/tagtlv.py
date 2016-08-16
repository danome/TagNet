import os, sys, types
from os.path import normpath, commonprefix

#from enum import Enum, unique
import enum

#@enum.unique
class tlv_types(enum.Enum):
    STRING                 =  1
    INTEGER                =  2
    GPS                    =  3
    TIME                   =  4
    NODE_ID                =  5


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
        tl = []
        if ((len(args) <> 1)
                  or (not args[0])
                  or (not isinstance(args[0], types.StringType)
                      and not isinstance(args[0],types.ListType))):
            print('error:',args)
        else:
            if isinstance(args[0], types.StringType):
                for t,v in (zip(self.zstring,normpath(args[0]).split(os.sep)[1:])):
                    tl.append(TagTlv(t,v))
            elif isinstance(args[0], TagTlvList):
                for tlv in args[0]:
                    tl.append(TagTlv(tlv))
            else: # isinstance(args[0], types.ListType)
                if isinstance(args[0][0], types.TupleType):
                    for t,v in args[0]:
                        tl.append(TagTlv(t,v))
                elif isinstance(args[0][0], TagTlv):
                    for tlv in args[0]:
                        tl.append(TagTlv(tlv))
                else:
                    print('error:', args, type(args[0][0]))
                                  
        super(TagTlvList,self).__init__(tl) 

    #------------ following methods extend base class  ---------------------

    def build(self):
        """
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
        """
        return self

    def pkt_len(self):  # needs fixup
        """
        sum up the sizes of each tlv based on packet space required
        """
        return sum([len(tlv) for tlv in self])
    
    def startswith(self, d):
        """
        check to see if this name begins withs with specified name. True if exactly prefix matches.
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
        return super(TagTlvList,self).extend(tl)

    def insert(self, i, o):
        """
        insert overloaded to handle possible format conversions of value in inserting object
        """
        return super(TagTlvList,self).insert(i,TagTlv(o))

    def __add__(self,o):
        """
        __add__ overloaded to handle possible format conversions of value in adding object
        """
        return super(TagTlvList,self).__add__(TagTlv(o))

#------------ end of class definition ---------------------


class TagTlv(object):
    def __init__(self, t, v=None):
        self.tuple = None
        self.update(t,v)

    def update(self, t, v=None):
        if (v is None):
            o = t
            if isinstance(o,TagTlv):
                t = o.tlv_type()
                v = o.tlv_value()
            elif isinstance(o,types.TupleType):
                t = o[0]
                v = o[1]
        if (t):
            if t == tlv_types.STRING:
                if isinstance(v, types.StringType):
                    self.tuple = (t, v)
            elif t == tlv_types.INTEGER:
                if  isinstance(v, types.IntType):
                    self.tuple =  (t, int(v))
            elif t == tlv_types.GPS:
                self.tuple =  (t, bytearray(str(v)))
            elif t == tlv_types.TIME:
                self.tuple =  (t, bytearray(str(v)))
            elif t == tlv_types.NODE_ID:
                self.tuple =  (t, bytearray(v))
        else:
            if isinstance(v, types.STRING): self.tuple =  (types.STRING, v)
            elif isinstance(tlv_types.INTEGER): self.tuple =  (tlv_types.INTEGER, int(v))
        if (not self.tuple):
            print('error tlv ({}): {}/{}'.format(type(t), t, v))
            
    def parse(self, fb):
        """
        """
        if (fb[1] != len(fb[2:])):
            print('tlv bad parse: {}'.format(fb.encode('hex')))
        self.tuple = (fb[0], fb[2:])

    def build(self):
        """
        """
        v = bytearray(b'')
        if self.tuple[0] is tlv_types.STRING:
            v = self.tuple[1]
        elif self.tuple[0] is tlv_types.INTEGER:
            v = str(self.tuple[1])
        elif self.tuple[0] is tlv_types.GPS:
            v = self.tuple[1]
        elif self.tuple[0] is tlv_types.TIME:
            v = str(self.tuple[1])
        elif self.tuple[0] is tlv_types.NODE_ID:
            v = self.tuple[1]
        return bytearray([self.tuple[0].value, len(v)]) + v

    def tlv_type(self):
        return self.tuple[0]

    def tlv_value(self):
        return self.tuple[1]

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '({}, {})'.format(self.tuple[0],self.tuple[1])

    def __len__(self):
        return 2 + len(self.tuple[1])

#------------ end of class definition ---------------------

def test():
    t1 = TagTlv(tlv_types.STRING,'abc')
    t2 = TagTlv(t1)
    o1 = t1.build()
    return t1,t2,o1
    
if __name__ == '__main__':
    test()

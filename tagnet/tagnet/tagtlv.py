import os, sys, types
from os.path import normpath, commonprefix

from tagdef import *

from enum import Enum, unique

@unique
class tlv_types(Enum):
    STRING                 =  1
    INTEGER                =  2
    GPS                    =  3
    TIME                   =  4
    NODE_ID                =  5


def forever(v):
    """
    Returns the same value it is instantiated with each time it is called using .next()
    """
    while True:
        yield (v)


class TlvList(list):
    """
    constructor for tag names, which consist of a list of tag tlv's that represent the hierachical order of
    name components as defined by the list.
    """
    zstring=forever(tlv_types.STRING)

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
            arg0 = args[0]
            if isinstance(arg0, types.StringType):
                for t,v in (zip(self.zstring,normpath(arg0).split(os.sep)[1:])):
                    tl.append(Tlv(t,v))
            elif isinstance(arg0, TlvList):
                for tlv in arg0:
                    tl.append(Tlv(tlv))
            else: # isinstance(arg0, types.ListType)
                for t,v in arg0:
                    tl.append(Tlv(t,v))
        super(TlvList,self).__init__(tl) 

    #------------ following methods extend base class  ---------------------

    def copy(self):
        """
        make a copy of this tlvlist in a new tlvlist object
        """
        return TlvList(self)

    def endswith(self, d):
        """
        """
        return self

    def format(self):
        """
        """
        fb = bytearray(b'')
        for tlv in self:
            fb += tlv.format()
        return fb

    def pkt_len(self):  # needs fixup
        """
        sum up the sizes of each tlv based on packet space required
        """
        return sum([len(tlv) for tlv in self])
    
    def parse(self, v):
        """
        """
        return self

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
            tl.append(Tlv(o))
        return super(TlvList,self).extend(tl)

    def insert(self, i, o):
        """
        insert overloaded to handle possible format conversions of value in inserting object
        """
        return super(TlvList,self).insert(i,Tlv(o))

    def __add__(self,o):
        """
        __add__ overloaded to handle possible format conversions of value in adding object
        """
        return super(TlvList,self).__add__(Tlv(o))

#------------ end of class definition ---------------------


class Tlv(object):
    def __init__(self, t, v=None):
        self.update(t,v)

    def update(self, t, v=None):
        if (not v):
            o = t
            if isinstance(o,Tlv):
                t = o.tuple[0]
                v = o.tuple[1]
            elif isinstance(o,types.TupleType):
                t = o[0]
                v = o[1]
            else:
                print('error tlv ({}): {}'.format(type(o), o))
        if (t):
            if t == tlv_types.STRING:
                if isinstance(v, types.StringType):
                    self.tuple = (t, v)
            elif t == tlv_types.INTEGER:
                if  isinstance(v, types.IntegerType):
                    self.tuple =  (t, int(v))
        else:
            if isinstance(v, types.STRING): self.tuple =  (types.STRING, v)
            elif isinstance(tlv_types.INTEGER): self.tuple =  (tlv_types.INTEGER, int(v))

    def parse(self, fb):
        """
        """
        if (fb[1] != len(fb[2:])):
            print('tlv bad parse: {}'.format(fb.encode('hex')))
        self.tuple = (fb[0], fb[2:])

    def build(self):
        """
        """
        return bytearray(self.type_is(), self.__len__(), self.value_is())

    def type_is(self):
        return self.tuple[0]

    def value_is(self):
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

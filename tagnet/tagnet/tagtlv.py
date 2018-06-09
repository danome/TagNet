from __future__ import print_function   # python3 print function
from builtins import *                  # python3 types
import os, sys, types, platform
from os.path import normpath, commonprefix
#from temporenc import packb, unpackb
from binascii import hexlify
from struct import Struct, pack, unpack
from datetime import datetime
from uuid import getnode as get_mac
import copy
import unittest
import enum
import re

# only make these names public
#
__all__ = ['TagTlvList',
           'TagTlv',
           'tlv_types',
           'tlv_errors',
           'TlvListBadException',
           'TlvBadException']

# Fundamental Types of TLV objects
#
class tlv_types(enum.Enum):
    NONE             =  0
    STRING           =  1
    INTEGER          =  2
    GPS              =  3
    UTC_TIME         =  4
    NODE_ID          =  5
    NODE_NAME        =  6
    OFFSET           =  7
    SIZE             =  8
    EOF              =  9
    VERSION          = 10
    BLOCK            = 11
    RECNUM           = 12
    RECCNT           = 13
    DELAY            = 14
    ERROR            = 15
    APP1             = 20
    APP2             = 21

class tlv_errors(enum.Enum):
    SUCCESS          =  0
    FAIL             =  1
    ESIZE            =  2
    ECANCEL          =  3
    EOFF             =  4
    EBUSY            =  5
    EINVAL           =  6
    ERETRY           =  7
    ERESERVE         =  8
    EALREADY         =  9
    ENOMEM           = 10
    ENOACK           = 11
    ETIMEOUT         = 12
    ESUBSYSDIS       = 13
    EODATA           = 14
    ELAST            = 15

#    FAIL             =  1   # Generic condition: backwards compatible
#    ESIZE            =  2   # Parameter passed in was too big.
#    ECANCEL          =  3   # Operation cancelled by a call.
#    EOFF             =  4   # Subsystem is not active
#    EBUSY            =  5   # The underlying system is busy; retry later
#    EINVAL           =  6   # An invalid parameter was passed
#    ERETRY           =  7   # A rare and transient failure: can retry
#    ERESERVE         =  8   # Reservation required before usage
#    EALREADY         =  9   # The device state you are requesting is already set
#    ENOMEM           = 10   # Memory required not available
#    ENOACK           = 11   # A packet was not acknowledged
#    ETIMEOUT         = 12   # operation timed out
#    ESUBSYSDIS       = 13   # subsystem is disabled (vs. off)
#    EODATA           = 14   # End Of DATA (e.g., file or record)
#    ELAST            = 15   # Last enum value

# structs used in packing and unpacking complex TLV types
#
version_struct   = Struct('HBB')
#  uint16_t     build;
#  uint8_t      minor, major;
#
gps_struct       = Struct('<iii')
#  int32_t      x, y, z;
#
rtctime_struct  = Struct('<HBBBBBBH')
#  uint16_t	sub_sec;                /* 16 bit jiffies (32KiHz) */
#  uint8_t	sec;                    /* 0-59 */
#  uint8_t	min;                    /* 0-59 */
#  uint8_t	hr;                     /* 0-23 */
#  uint8_t      dow;                    /* day of week, 0-6, 0 sunday */
#  uint8_t	day;                    /* 1-31 */
#  uint8_t	mon;                    /* 1-12 */
#  uint16_t	yr;


# General Functions
#
def _forever(v):
    """
    Returns the same value it is instantiated with each time it is called using .next()
    """
    while True:
        yield (v)

def int_to_tlv_type(idx):
    """
    Returns the network format (byte) value of TLV type
    """
    for tlvt in tlv_types:
        if (tlvt.value == idx): return tlvt
    return None

#------------ end of general functions  ---------------------


class TlvBadException(Exception):
    def __init__( self, t, v):
        self.t = t
        self.v = v
        if isinstance(v, bytearray):
            v = str(len(v)) + '.' + hexlify(v)
        Exception.__init__(self, 'Bad Tlv: type:{}, value:{}'.format(
            t if (t) else 'None',
            v if (v) else 'None'))

class TlvListBadException(Exception):
    def __init__( self, args):
        self.args = args
        Exception.__init__(self, 'Bad Tlv List: args:{}'.format(
            args if (args) else 'None'))

#------------ end of exception classes  ---------------------


class TagTlvList(list):
    """
    constructor for Tag TLV lists.

    Used in specifying tag names and payloads.
    """
    zstring=_forever(tlv_types.STRING)

    def __init__(self, *args, **kwargs):
        """
        initialize the tagtlv list structure

        If no parameter, then return empty TagTlvList

        One parameter of one of the following types:
        - String
        - bytearray
        - TagTlvList
        - list of TagTlvs [tlv, ...]
        - list of tuples [(type, value)...]
        - TagTlv (singleton)

        More than one parameter then treat as list of TLVs.

        Make sure that all elements added are valid tlv_types.
        """
        super(TagTlvList,self).__init__()
        if (len(args) == 0):
            pass
        elif (len(args) == 1):
            # zzz print(type(args[0]))
            if isinstance(args[0], types.StringType):
                for t,v in zip(self.zstring,
                               normpath(args[0]).split(os.sep)):
                    if (v == ''):
                        continue
                    self.append(TagTlv(t,v))
            elif isinstance(args[0], bytearray):
                self.parse(args[0])
            elif isinstance(args[0], TagTlvList):
                for tlv in args[0]:
                    self.append(TagTlv(tlv))
            elif isinstance(args[0][0], types.TupleType):
                for t,v in args[0]:
                    self.append(TagTlv(t,v))
            elif isinstance(args[0][0], TagTlv):
                for tlv in args[0]:
                    self.append(TagTlv(tlv))
            else:
                raise TlvListBadException(args)
        else:
            tl = []
            for arg in args:
                tl.append(TagTlv(arg))
            super(TagTlvList,self).extend(tl)
            #except:
            #    raise TlvListBadException(args)

    #------------ following methods extend base class  ---------------------

    def build(self):
        """
        construct the packet formatted string from tagtlvlist
        """
        fb = bytearray(b'')
        for tlv in self:
            fb.extend(tlv.build())
        return fb

    def copy(self):
        """
        make a copy of this tlvlist in a new tlvlist object
        """
        return copy.deepcopy(self)

    def endswith(self, d):
        """
        """
        return self

    def parse(self, fb):
        """
        process nextwork formatted string of tlvs into a tagtlvlist. replaces current list
        """
        x = 0
        while (x < len(fb)):
            y = fb[x+1] + 2
            self.append(TagTlv(fb[x:x+y]))
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

    def append(self, t):
        """
        append overloaded to handle possible format conversions of value in appending object
        """
        self.extend([t])

    def extend(self, l):
        """
        extend overloaded to handle possible format conversions of value in extending list
        """
        tl = []
        for t in l:
            tl.append(TagTlv(t))
        super(TagTlvList,self).extend(tl)

    def insert(self, i, t):
        """
        insert overloaded to handle possible format conversions of value in inserting object
        """
        super(TagTlvList,self).insert(i,TagTlv(t))

    def __add__(self, other):
        """
        __add__ overloaded to handle possible format conversions of value in adding object
        """
        tl = copy.copy(self)
        if isinstance(other, TagTlv):
            tl.append(TagTlv(other))
        elif isinstance(other, TagTlvList):
            tl = TagTlvList(other).extend(TagTlvList(self))
        return tl

    def __radd__(self, other):
        """
        __add__ overloaded to handle possible format conversions of value in adding object
        """
        if isinstance(other, TagTlv):
            self.append(TagTlv(other))
        elif isinstance(other, TagTlvList):
            self.extend(TagTlvList(other))
        return self


#------------ end of class definition ---------------------

class _Tlv(object):
    """
    internal class for handling basic tlv manipulation

    returns none if operation fails
    """
    def __init__(self, t, v=None):
        """
        Create basic Tlv object instance

        Translates from Python variable to TagTlv network
        bytearray.

        When only one parameter, use as bytearray in network
        format and verify its validity.

        Tlv is internally stored in the network format.

        Can be retrieved in network format with self.build()
        or as Python object with self.value()
        """
        self.mytuple   = None

        if v is None:
            if isinstance(t, bytearray):
                # zzz print('tlv.__init__', hexlify(t))
                # if the value can be built, then good tlv
                if (self._build_value(t) is not None):
                    # check tlv len field eq len of value
                    if (len(t[2:]) == t[1]):
                        self.mytuple = copy.copy(t)
        else:
            self.mytuple = self._build_tlv(t, v)
        if (self.mytuple is None):
            raise TlvBadException(t, v)

    def tlv_type(self):
        """
        returns value of the tlv type for this TLV
        """
        if (self.mytuple):
            return int_to_tlv_type(self.mytuple[0])
        return (tlv_types.None)

    def value(self):
        """
        returns the python object representing tlv value
        """
        return self._build_value(self.mytuple)

    def build(self):
        """
        returns the tlv network byte array
        """
        return bytearray(self.mytuple)

    def __len__(self):
        """
        returns the length of tlv network byte array
        """
        if (self.mytuple):
            return len(self.mytuple)
        return 0

    def __eq__(self, other):
        return (self.mytuple == other.mytuple)

    def __ne__(self, other):
        return not self.__eq__(other)

    def _to_tlv(self, t, v):
        """
        add tlv header to network byte array
        """
        # zzz print(type(t))
        if isinstance(t, type(tlv_types.NONE)): # match any tlv_type
            # zzz print('here')
            hdr = pack('BB', t.value, len(v))
            # zzz print(hexlify(hdr))
            return bytearray(hdr + bytearray(v))
        # zzz print('bad tlv')
        raise TlvBadException(t, v)

    def _to_tlv_int(self, t, v):
        """
        compress integer and add tlv header to network byte array
        """
        n = int(v)
        p = pack('>L', n)
        for i in range(0,4):
            if (p[i] != '\x00'): break
        return self._to_tlv(t, p[i:])

    def _build_tlv(self, t, v):
        """
        construct a network byte array from a type-value pair
        """
        if (t == tlv_types.INTEGER) or \
           (t == tlv_types.OFFSET) or \
           (t == tlv_types.RECNUM) or \
           (t == tlv_types.RECCNT) or \
           (t == tlv_types.DELAY) or \
           (t == tlv_types.SIZE):
            if isinstance(v, types.IntType) or \
               isinstance(v, types.LongType):
                return self._to_tlv_int(t, v)

        if (t == tlv_types.ERROR):
            if isinstance(v, tlv_errors):
                return self._to_tlv_int(t, v.value)

        if (t == tlv_types.STRING)or \
           (t == tlv_types.NODE_NAME):
            if isinstance(v, types.StringType) or \
               isinstance(v, bytearray):
                return self._to_tlv(t, bytearray(v))

        if (t == tlv_types.GPS):
            if isinstance(v, tuple) or isinstance(v, list):
                ba = gps_struct.pack(*v)
                return self._to_tlv(t, bytearray(ba))

#  uint16_t	sub_sec;                /* 16 bit jiffies (32KiHz) */
#  uint8_t	sec;                    /* 0-59 */
#  uint8_t	min;                    /* 0-59 */
#  uint8_t	hr;                     /* 0-23 */
#  uint8_t      dow;                    /* day of week, 0-6, 0 sunday */
#  uint8_t	day;                    /* 1-31 */
#  uint8_t	mon;                    /* 1-12 */
#  uint16_t	yr;
        if (t == tlv_types.UTC_TIME):
            if isinstance(v, datetime):
                ba = rtctime_struct.pack(v.microsecond / 31,
                                         v.second,
                                         v.minute,
                                         v.hour,
                                         v.weekday(),
                                         v.day,
                                         v.month,
                                         v.year)
                return self._to_tlv(t, ba)

        if (t == tlv_types.NODE_ID):
            if isinstance(v, types.IntType) or\
               isinstance(v, types.LongType):
                ba = bytearray.fromhex(
                    ''.join('%02X' % ((v >> 8*i) & 0xff) for i in xrange(6)))
            elif isinstance(v, types.StringType):
                ba = bytearray.fromhex(v)
            elif isinstance(v, bytearray):
                ba = v
            if (ba):
                return self._to_tlv(t, ba)
            raise TlvBadException(t, v)

        if (t == tlv_types.EOF):    return self._to_tlv(t, bytearray(''))

        if (t == tlv_types.VERSION):
            # zzz print(type(v))
            if isinstance(v, list) or \
               isinstance(v, tuple):
                major, minor, build = v
                # zzz print(type(major),major,minor,build)
                ba = version_struct.pack(int(build), int(minor), int(major))
                btlv = self._to_tlv(t, bytearray(ba))
                # zzz print(btlv)
                return btlv

        if (t == tlv_types.BLOCK) or \
           (t == tlv_types.APP1)  or \
           (t == tlv_types.APP2):
            return self._to_tlv(t, v)

        raise TlvBadException(t, v)

    def _build_value(self, ba):
        """
        construct a python object from network byte array
        """
        def int_to_value(v):
            """
            Returns an integer from converting the network (byte string) value
            """
            try:
                acc = 0
                for i in range(l): acc = (acc << 8) + v[i]
                return acc
            except:
                return None

        def err_to_value(v):
            """
            Returns a tlv_errors type from converting the network (byte string) value
            """
            try:
                acc = 0
                err = tlv_errors.SUCCESS
                for i in range(l): acc = (acc << 8) + v[i]
                for n in tlv_errors.__dict__['_member_names_']:
                    err = eval('tlv_errors.'+n)
                    if err.value == acc:
                        return err
                return none
            except:
                return None

        if (len(ba) < 2):
            raise TlvBadException(ba, None)
        t = int_to_tlv_type(ba[0])
        l = ba[1]
        v = ba[2:]
        # zzz print(t,l,hexlify(v))
        if (len(v) != l):
            raise TlvBadException(t, v)
        if (t == tlv_types.INTEGER):   return int_to_value(v)
        if (t == tlv_types.STRING):    return bytearray(v)
        if (t == tlv_types.GPS):       return list(gps_struct.unpack(v))
        if (t == tlv_types.UTC_TIME):
            jiffy, second, minute, hour, dow, day, month, year \
                                               = rtctime_struct.unpack(v)
            # dt = datetime.utcnow() # zzz fake date until tag has right content
            try:
                dt = datetime(year, month, day, hour, minute, second,
                              int(jiffy * (1000000./32768)))
            except TypeError:
                print('*** tagtlv.build.rtctime',
                      year, month, day, hour, minute, second, jiffy)
                raise TlvBadException(t, v)
            # zzz print('*** tagtlv._build_value',dt)
            return dt
        if (t == tlv_types.NODE_ID):   return v
        if (t == tlv_types.NODE_NAME): return bytearray(v)
        if (t == tlv_types.OFFSET):    return int_to_value(v)
        if (t == tlv_types.SIZE):      return int_to_value(v)
        if (t == tlv_types.EOF):       return True
        if (t == tlv_types.VERSION):
            build, minor, major = version_struct.unpack(v)
            return (major, minor, build)
        if (t == tlv_types.BLOCK):     return copy.deepcopy(v)
        if (t == tlv_types.RECNUM):    return int_to_value(v)
        if (t == tlv_types.RECCNT):    return int_to_value(v)
        if (t == tlv_types.DELAY):     return int_to_value(v)
        if (t == tlv_types.ERROR):     return err_to_value(v)
        if (t == tlv_types.APP1):      return copy.deepcopy(v)
        if (t == tlv_types.APP2):      return copy.deepcopy(v)
        raise TlvBadException(t, v)

#------------ end of class definition ---------------------


class TagTlv(object):
    """
    Constructor for a TagNet Type-Length-Value (TLV) Object

    Handles the translation between network format and
    python types.
    """
    def __init__(self, t=None, v=None):
        """
        initializes the specified TLV type and value

        When invoked with zero parameters, just create empty
        tlv.

        When invoked with two parameters, the first parameter
        is the tlv_type, and the second is the data associated
        with this type, in its Python form.

        When invoked with one parameter, then handle by type
        as follows:
        - integer or long   = convert number to integer tlv
        - string            = convert string to string tlv
        - bytearray         = parse network format to tlv
        - tuple(t,v)        = convert tuple(tlv, value) to tlv
        - TagTlv            = create new tlv, copy type/value
        """
        self.mytlv = None  # value of tlv associated with this object
        if (t is None) and (v is None):       # no parameters
            pass                              #  empty list
        elif (t is not None and v is not None): # two parameters
            self.mytlv = _Tlv(t,v)              #  tuple
        elif (v is None):                     # one parameter
            if isinstance(t, types.IntType) or \
               isinstance(t, types.LongType):       # Integer
                self.mytlv = _Tlv(tlv_types.INTEGER, t)
            elif isinstance(t, types.StringType):     # String
                self.mytlv = self._regex_tlv(t) if (t[0] is '<') \
                      else _Tlv(tlv_types.STRING, t)
            elif isinstance(t, bytearray):            # bytearray
                self.mytlv = _Tlv(t)
            elif isinstance(t, types.TupleType):      # Tuple
                self.mytlv = _Tlv(t[0], t[1])
            elif (isinstance(t, TagTlv)):             # TagTlv
                self.mytlv = _Tlv(t.tlv_type(), t.value())
            elif (t == tlv_types.EOF):
                self.mytlv = _Tlv(t, bytearray(b''))
        if (self.mytlv is None):
            raise TlvBadException(t, v)

    def _regex_tlv(self, buf):
        # zzz print('regex_tlv', type(buf), buf)
        try:
            # zzz print('try version')
            key, major, minor, build = \
                re.findall('^<(.{1,}):([0-9]{1,5})\.([0-9]{1,3})\.([0-9]{1,3})>',
                           buf.upper())[0]
            # zzz print(key, major, minor, build)
            if (key == 'VERSION'):
                return _Tlv(tlv_types.VERSION,
                            (int(major),int(minor),int(build)))
        except IndexError, ValueError:
            pass
        try:
            key, value = buf[1:-1].split(':')
            # zzz print('try node_id')
            key, value = re.findall('^<(.{1,}):([0-9A-F]+)>',
                                    buf.upper())[0]
            # zzz print(key, type(value), value)
            if (key == 'NODE_ID'):
                return _Tlv(tlv_types.NODE_ID,
                            value)
        except IndexError, ValueError:
            raise TlvBadException(t, v)
        return None # shouldn't get here

    def copy(self):
        return copy.deepcopy(self)

    def update(self, t, v=None):
        """
        modify existing type and value fields of object
        """
        if (v):
            self.mytlv = _Tlv(t, v)
            if (self.mytlv):
                return
        if isinstance(t, TagTlv):
            self.mytlv = _Tlv(t.tlv_type(),t.value())
            if (self.mytlv):
                return
        if isinstance(t, types.TupleType):
            self.mytlv = _Tlv(t[0],t[1])
            if (self.mytlv):
                return
        raise TlvBadException(t, v)

    def parse(self, ba):
        """
        parse network formatted tlv into object instance
        """
        self.mytlv = _Tlv(ba)
        if (self.mytlv is None):
            raise TlvBadException(self.mytlv, None)

    def build(self):
        """
        build a network formatted tlv from object instance
        """
        if (self.mytlv):
            return self.mytlv.build()
        raise TlvBadException(self.mytlv, None)

    def tlv_type(self):
        return self.mytlv.tlv_type()

    def value(self):
        return self.mytlv.value()

    def __add__(self, other):
        if isinstance(other, TagTlv):
            return TagTlvList([other,self])
        elif isinstance(other, TagTlvList):
              return TagTlvList([self]) + TagTlvList(other)
        return None

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.mytlv.__eq__(other.mytlv))
#            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        try:
            v = self.mytlv.value()
            if (self.tlv_type() == tlv_types.NODE_ID):
                v = hexlify(v)
            return '({}, {})'.format(self.mytlv.tlv_type(),v)
        except:
            raise TlvBadException(self.mytlv, None)

    def __len__(self):
        return self.mytlv.__len__()

#------------ end of class definition ---------------------

class TestTlvMethods(unittest.TestCase):
    def setUp(self):
        self.tstr = TagTlv(tlv_types.STRING, b'abc')
        self.ttlv = TagTlv(self.tstr)
        pass

    def tearDown(self):
        del self.tstr
        del self.ttlv
        pass

#    @unittest.skip("skip  ")
    def test_tlv_string(self):
        ostr = self.tstr.build()
        xstr = TagTlv(ostr)
        self.assertEqual(xstr, self.tstr)
        self.assertIsNot(xstr, self.tstr)
        self.assertEqual(xstr.tlv_type(), tlv_types.STRING)
        self.assertEqual(xstr.value(), 'abc')
        self.assertEqual(len(xstr), 5)

#    @unittest.skip("skip  ")
    def test_tlv_integer(self):
        tint1 = TagTlv(tlv_types.INTEGER, 1)
        tint10k = TagTlv(tlv_types.INTEGER, 10000)
        oint1 = tint1.build()
        oint10k = tint10k.build()
        tint1.parse(oint1)
        tint10k.parse(oint10k)
        self.assertNotEqual(self.tstr, tint1)
        self.assertEqual(tint1.value(), 1)
        self.assertEqual(tint10k.value(), 10000)
        self.assertEqual(len(tint1), 3)
        self.assertEqual(len(tint10k), 4)

#    @unittest.skip("skip gps")
    def test_tlv_gps(self):
#        (lat:37.04903, lon:-122.02625, elev:191.14464)
#        (x:-2702906, y:-4321156, z:3821852)
        pass

#    @unittest.skip("skip datetime")
    def test_tlv_datetime(self):
        tm = datetime.now().strftime("%c")
        ttime = TagTlv(tlv_types.UTC_TIME, tm)
        otime = ttime.build()
        xstr = TagTlv(otime)
        self.assertEqual(xstr.value(), tm)

#    @unittest.skip("skip node id")
    def test_tlv_node_id(self):
        tnid1 = TagTlv(tlv_types.NODE_ID, get_mac())
        tnid2 = TagTlv(tlv_types.NODE_ID, ''.join('%02X' % ((get_mac() >> 8*i) & 0xff) \
                                                  for i in xrange(6)))
        self.assertEqual(hexlify(tnid1.value()), hexlify(tnid2.value()))
        self.assertEqual(tnid1, tnid2)
        onid1 = tnid1.build()
        onid2 = tnid2.build()
        self.assertEqual(onid1, onid2)
        self.assertEqual(tnid1, TagTlv(onid1))
        self.assertEqual(tnid2, TagTlv(onid2))

#    @unittest.skip("skip node name")
    def test_tlv_node_name(self):
        tnn =  TagTlv(tlv_types.NODE_NAME, platform.node())
        onn = tnn.build()
        self.assertEqual(tnn.value(), platform.node())
        self.assertEqual(tnn, TagTlv(onn))
        tnn.parse(self.tstr.build())
        self.assertNotEqual(tnn, TagTlv(onn))

#    @unittest.skip("skip offset")
    def test_tlv_offset(self):
        tof =  TagTlv(tlv_types.OFFSET, 129000)
        oof = tof.build()
        self.assertEqual(tof.value(), 129000)
        self.assertEqual(tof, TagTlv(oof))
        tof.parse(self.tstr.build())
        self.assertNotEqual(tof.tlv_type(), TagTlv(oof).tlv_type())

#    @unittest.skip("skip size")
    def test_tlv_size(self):
        tsz =  TagTlv(tlv_types.SIZE, 12345678)
        osz = tsz.build()
        self.assertEqual(tsz.value(), 12345678)
        self.assertEqual(tsz, TagTlv(osz))
        tsz.parse(self.tstr.build())
        self.assertNotEqual(tsz.value(), TagTlv(osz).value())

#    @unittest.skip("skip eof")
    def test_tlv_eof(self):
        teof = TagTlv(tlv_types.EOF)
        oeof = teof.build()
        self.assertEqual(teof.tlv_type(), tlv_types.EOF)
        self.assertEqual(teof.value(), TagTlv(oeof).value())
        self.assertEqual(teof.value(), bytearray(b''))

#    @unittest.skip("skip version")
    def test_tlv_error(self):
        vers = (1, 16, 0)
        vtlv = TagTlv(tlv_types.ERROR, tlv_errors.ENOMEM)
        self.assertEqual(tlv_errors.ENOMEM, vtlv.value())
        ovtlv = vtlv.build()
        self.assertEqual(tlv_errors.ENOMEM, TagTlv(ovtlv).value())

#    @unittest.skip("skip version")
    def test_tlv_version(self):
        vers = (1, 16, 0)
        vtlv = TagTlv(tlv_types.VERSION, vers)
        self.assertEqual(list(vers), vtlv.value())
        vers = [1, 16, 0]
        vtlv = TagTlv(tlv_types.VERSION, vers)
        self.assertEqual(vers, vtlv.value())
        ovtlv = vtlv.build()
        self.assertEqual(vers, TagTlv(ovtlv).value())

#    @unittest.skip("skip block")
    def test_tlv_block(self):
        import pickle
        blocks = pickle.dumps(self.tstr)
        tbl = TagTlv(tlv_types.BLOCK, blocks)
        obl = tbl.build()
        self.assertEqual(tbl.value(), TagTlv(obl).value())
        blocko = pickle.loads(TagTlv(obl).value())
        self.assertEqual(self.tstr, blocko)

#    @unittest.skip("skip __init__ using tlv")
    def test_tlv_init_tlv(self):
        ttlv = TagTlv(self.tstr)
        tclv = TagTlv(ttlv)
        self.assertEqual(ttlv, tclv)

#    @unittest.skip("skip __init__ using bytearray")
    def test_tlv_init_bytearray(self):
        tba = TagTlv(bytearray.fromhex(b'0103746167'))
        self.assertEqual(tba.tlv_type(), tlv_types.STRING)
        self.assertEqual(tba.value(), 'tag')

class TestTlvListMethods(unittest.TestCase):
    def setUp(self):
        self.tlempty = TagTlvList('')
        self.tlstr = TagTlvList('/foo/bar')
        self.olstr = self.tlstr.build()
        self.tlba = TagTlvList(bytearray.fromhex(b'01037461670104706f6c6c'))
        self.tllist = TagTlvList(self.tlstr)

    def tearDown(self):
        del self.tlempty
        del self.tlstr
        del self.olstr
        del self.tlba
        del self.tllist
        pass

#    @unittest.skip("skip  __init__ string")
    def test_tlvlist_init_string(self):
        self.assertEqual(self.tlstr, TagTlvList(self.olstr))

#    @unittest.skip("skip __init__ using tlvlist")
    def test_tlvlist_init_tlvlist(self):
        self.assertEqual(self.tlstr, self.tllist)

#    @unittest.skip("skip __init__ using byte array")
    def test_tlvlist_init_bytearray(self):
        self.assertEqual(self.tlba, TagTlvList(self.tlba.build()))

#    @unittest.skip("skip __init__ using list of tuples")
    def test_tlvlist_init_tuples(self):
        tltups = TagTlvList([(tlv_types.STRING, 'bang'),
                             (tlv_types.STRING,'woof woof'),
                             ])
        self.assertEqual(tltups, TagTlvList(tltups.build()))

#    @unittest.skip("skip __init__ using list of tlvs")
    def test_tlvlist_init_tlvs(self):
        lst = [TagTlv(tlv_types.STRING,'abc'),
               TagTlv(tlv_types.INTEGER, 1),
               TagTlv(tlv_types.GPS, (-2702906, -4321156, 3821852)),
               ]
        tltlvs = TagTlvList(lst)
        lst = [TagTlv(tlv_types.UTC_TIME, "time"),
               TagTlv(tlv_types.NODE_NAME, platform.node()),
               ]
        tltlvs = TagTlvList(lst)
        lst = [TagTlv(tlv_types.NODE_ID, get_mac()),
               ]
        tltlvs = TagTlvList(lst)
        lst = [TagTlv(tlv_types.STRING,'abc'),
               TagTlv(tlv_types.OFFSET, 45678),
               TagTlv(tlv_types.SIZE, 12345678),
               TagTlv(tlv_types.EOF),
               ]
        tltlvs = TagTlvList(lst)
        lst = [TagTlv(tlv_types.STRING,'abc'),
               TagTlv(tlv_types.VERSION, (121, 16, 0)),
               TagTlv(tlv_types.BLOCK, bytearray('abc')),
               ]
        tltlvs = TagTlvList(lst)
        self.assertEqual(tltlvs, TagTlvList(tltlvs.build()))

#    @unittest.skip("skip __init__ using multiple parameters")
    def test_tlvlist_init_params(self):
        tl = TagTlvList('foo','bar')
        self.assertEqual(self.tlstr, tl)
        tl += [TagTlv(tlv_types.VERSION, (1,16,0))]
        ol = tl.build()
        tl2 = TagTlvList('foo','bar', (tlv_types.VERSION, (1,16,0)))
        self.assertEqual(TagTlvList(ol), tl2)


#    @unittest.skip("skip append to tlvlist")
    def test_tlvlist_append(self):
        tl = TagTlvList('/')
        tl.append(TagTlv('foo'))
        tl.append(TagTlv('bar'))
        self.assertEqual(self.tlstr, tl)
        tl = TagTlvList()
        tl.append(TagTlv('foo'))
        tl.append(TagTlv('bar'))
        self.assertEqual(self.tlstr, tl)
        tl = TagTlvList('')
        tl.append(TagTlv('foo'))
        tl.append(TagTlv('bar'))
        self.assertNotEqual(self.tlstr, tl)

#    @unittest.skip("skip extend a tlvlist")
    def test_tlvlist_extend(self):
        tl = TagTlvList('foo')
        tl.extend([TagTlv('bar')])
        self.assertEqual(self.tlstr, tl)

#    @unittest.skip("skip add to tlvlist ")
    def test_tlvlist_add(self):
        tl = TagTlvList('foo')
        tl += [TagTlv('bar')]
        self.assertEqual(self.tlstr, tl)


if __name__ == '__main__':
    unittest.main()

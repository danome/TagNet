from __future__ import print_function   # python3 print function
from builtins import *

from si446xdef import *
from construct import *
from time import time, ctime, mktime, localtime, strptime, strftime
import sys

import types
import binascii

__all__ = ['Trace', 'RingBuffer', 'si446xtrace_test']

default_format = '%Y.%m.%d %H:%M:%S'

class Trace:
    """
    Radio Trace Handler

    This class provides control and support functions for low level radio
    trace handling. The trace events are added to a circular buffer that
    can be displayed when needed.
    """
    def __init__(self, size, form=default_format, rb=None):
        """
        Initialize new Trace buffer

        If no ringbuffer is specified, allocate a new ringbuffer.
        Also optionally provide the format for presenting time.
        """
        if (rb):
            self.rb = rb
            self.size = rb.len()
        else:
            self.rb = RingBuffer(size)
            self.size = size
        self.index = 0
        self.date_f=form
        self.disabled = False

    def add(self, where, data, s_name='string', level=1):
        """
        add a new trace record.

        A trace record consists of:
        -  where   a well known name for the record type, (see RadioTraceIds),
        -  data    the content to be added in the trace record
        -  s_name  an optional name of the structure used to decode contents, and
        -  level   the number of stack frames to include for call history
        """
        if (self.disabled):
            return
        sig = ' '
        stack = []
        for x in range(level+1,1,-1):
            try:
                stack.append(
                    (sys._getframe(x).f_code.co_name, sys._getframe(x).f_lineno))
            except:
                continue
        for fn,ln in stack[-level:]:
            sig += ' {}:{}'.format(fn,ln)
        self.index += 1
        self.rb.append((time(), where, sig, s_name, self.index, bytearray(data)))

    def _disable(self):
        """
        Turn off tracing
        """
        self.disabled = True

    def _enable(self):
        """
        Turn on tracing (initial state)
        """
        self.disabled = False

    def format_time(self, t, form=None):
        """
        Format time value into presentation string

        t = time.time() -> 1475131726.001496
        format_time(t)  -> '2016.09.28 23:49:05.262983'
        """
        f = form if (form) else self.date_f
        return strftime(f,localtime(t))+'.{:.6}'.format(str(t%1)[2:])

    def parse_time(self, s):
        """
        Convert a formatted time string into time value

        s               -> '2016.09.28 23:49:05.262983'
        parse_time(s)   -> 1475131726.001496
        """
        return mktime(strptime(s[:-7],self.date_f))+float('.'+s[-6:])

    def format(self,t,where,sig,s_name,index,data,form=None):
        """
        Format a trace record

        format a trace record using:
        -  t            time,
        -  where        record type,
        -  signature    stack trace, and
        -  s_name       structure for converting data
        -  index        record number
        -  data         associated data
        """
        if ((where == 'RADIO_PEND') or
            (where == 'RADIO_CMD') or
            (where == 'RADIO_RSP') or
            (where == 'RADIO_DUMP') or
            (where == 'RADIO_FRR') or
            (where == 'RADIO_FSM') or
            (where == 'RADIO_GROUP')):
            s = ' {} '.format(s_name)
            try:
                my_struct = eval(s_name)
                s += radio_display_structs[my_struct](my_struct, data)
            except:
                if ((s_name == 'string') or isinstance(data, types.StringType)):
                    s += data
                else:
                    s += binascii.hexlify(data)
        else:
            s = ' ' + str(data)
        last_d = t-self.last_t if (self.last_t) else 0
        mark_d = t-self.mark_t if (self.mark_t) else 0
        if (mark_d):
            delta_s = ' {:.6f}, {:.6f}'.format(last_d,mark_d)
        else:
            delta_s = ' {:.6f}'.format(last_d)
        tt = self.format_time(t, form)
        return [tt,delta_s,where,sig,index,s]
#        f = '{:^6}; {}; {}; {}; {}; {} '.format(index,tt,delta_s,where,sig,len(s))
#        return f + s

    def filter(self, filter=None, count=0, begin=None, mark=None, span=0):
        """
        Return list of Trace records based on filter parameters

        filter    is   one or more trace Id names to filter results
        count     is   how many records to return (positive=oldest,negative=newest)
        begin     is   timestamp where to start
        mark      is   remember this place and compare to time of next match
        span      is   when filtering, display more than one record when matched
        """
        self.last_t = 0
        self.mark_t = 0
        span_d = 0
        depth = -1
        begin_t =  self.parse_time(begin) if (begin) else 0
        if (count < 0):
            count = abs(count)
            if (filter):
                xb = RingBuffer(count)
                n = 0
                for t,where,sig,s_name,index,data in self.rb.get():
                    if where in filter:
                        xb.append(n)
                    n += 1
                depth = self.rb.len() - xb.last()
            else:
                depth = count if (count < self.rb.len()) else -1
        elif (count == 0):
            count = self.size
        recs = []
        for t,where,sig,s_name,index,data in self.rb.peek(depth):
            if (span_d):
                span_d -= 1
            else:
                if (filter):
                    if (where in filter):
                        if (span):
                            span_d = span-1
                    else:
                        continue
                if ((begin) and (begin_t > t)):
                    continue
                if (where == mark):
                    self.mark_t = t
                count -= 1
            self.last_t = t
            if ((not span_d) and (count < 0)):
                break
            recs.append((t,where,sig,s_name,index,bytearray(data)))
        return recs

    def display(self, entries):
        """
        Return list of formated trace records
        """
        ds = []
        for t,where,sig,s_name,index,data in entries:
            ds.append(self.format(t,where,sig,s_name,index,bytearray(data)))
        return ds
#end class

class RingBuffer:
    """
    in-memory ringbuffer used to hold the trace records. note that the
    class is modified to handle first full wrap differently
    """
    def __init__(self,size_max):
        self.max   = size_max
        self.data  = []
        self.cur   = 0
    def len(self):
        return len(self.data)
    def append(self,x):
        """append an element at the end of the buffer"""
        self.data.append(x)
        if (self.len() == self.max):
            self.cur=0
            self.__class__ = self.RingBufferFull
    def peek(self,n):
        """ return the newest elements, oldest first"""
        n = 0 if ((n >= self.len()) or (n == -1)) else self.len() - n
        return self.data[n:] if (self.data) else []
    def last(self):
        """return the oldest element"""
        return self.data[0] if (self.data) else -1
    def get(self):
        """ return a list of elements from the oldest to the newest"""
        return self.data
    class RingBufferFull:
        """
        same class definition, but handles the wrapped case
        """
        def __init__(self,n):
            raise "you should use RingBuffer"
        def len(self):
            return len(self.data)
        def append(self,x):
            self.data[self.cur]=x
            self.cur=(self.cur+1) % self.max
        def peek(self, n):
            """ return the newest elements, oldest first"""
            n = self.max if ((n > self.max) or (n == -1)) else n
            x = 0 if (n > self.cur) else self.cur - n
            if (n <= self.cur):
                y = self.max
            else:
                nx = n - self.cur
                y = self.cur if (nx > (self.max - self.cur)) else self.max - nx
            return self.data[y:self.max]+self.data[x:self.cur]
        def last(self):
            """return the oldest element"""
            n = self.cur if (self.cur < self.max) else 0
            return self.data[n]
        def get(self):
            return self.data[self.cur:]+self.data[:self.cur]
#end class

# test
#
def spi(t, w, cmd, s_name):
    t.add(w, cmd, s_name, level=2)

def f2(t):
    response = fast_frr_s.parse('\x08\x00\x0c\x84')
    response.ph_pend.FILTER_MATCH = True
    rsp = fast_frr_s.build(response)
    spi(t, 'RADIO_FRR', rsp, fast_frr_s.name)
    response = fast_frr_rsp_s.parse('\xff\x08\x00\x0c\x84')
    rsp = fast_frr_rsp_s.build(response)
    spi(t, 'RADIO_PEND', rsp, fast_frr_rsp_s.name)

def f1(t):
    request = change_state_cmd_s.parse('\x00' * change_state_cmd_s.sizeof())
    request.cmd = 'CHANGE_STATE'
    request.state = 'SPI_ACTIVE'
    cmd = change_state_cmd_s.build(request)
    spi(t, 'RADIO_CMD', cmd, change_state_cmd_s.name)

def f0(t):
    f1(t)
    if (t.rb.len() != len(t.filter())): print("filter.len {} not equal to ringbuffer.len {}".format(t.rb.len(),len(t.filter())))
    f2(t)
    if (t.rb.len() != len(t.rb.peek(-1))):  print("filter.len {} not equal to peek.len {}".format(t.rb.len(),len(t.filter())))

def si446xtrace_test():
    t = Trace(10)
    f0(t)
    i=time()
    s=t.format_time(i)
    o=t.parse_time(s)
    if "{:0.4f}".format(i) != "{:0.4f}".format(o): print('si446xtrace_test fail, i:{0:0.4f} should equal o:{0:0.4f}'.format(i,o))
    f0(t)
    f0(t)
    f0(t)
    f0(t)
    f0(t)
    return i,o,s,t

if __name__=='__main__':
    i,o,s,t = si446xtrace_test()
    for e in t.display(t.filter()):
        print(e)

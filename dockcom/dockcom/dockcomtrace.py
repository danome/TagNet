from __future__ import print_function   # python3 print function
from builtins import *

from si446xdef import *
from construct import *
from time import time, ctime, mktime, localtime, strptime, strftime
import sys

from binascii import hexlify

__all__ = ['Trace', 'RingBuffer', 'si446xtrace_test']

class Trace:
    """
    This class provides control and support functions for low level radio
    trace handling. The trace events are added to a circular buffer that
    can be displayed when needed.
    """
    def __init__(self, size, form='%Y.%m.%d %H:%M:%S', rb=None):
        self.rb = rb if (rb) else RingBuffer(size)
        self.size = size
        self.index = 0
        self.date_f=form
        self.disabled = False
        
    def add(self, where, data, s_name='string', level=1):
        """
        add a new trace record. where is a well known name for the record type,
        s_name is an optional name of the structure used to decode contents,
        and level is the number of stack frames to include for call history
        """
        if (self.disabled):
            return
        where_id = radio_trace_ids.by_name(where)
        sig = ' '
        stack = []
        for x in range(level+1,1,-1):
            try:
                stack.append(
                    (sys._getframe(x).f_code.co_name, sys._getframe(x).f_lineno))
            except:
                continue
        for fn,ln in stack[-level:]:
            sig += '{}:{} -> '.format(fn,ln)
        self.rb.append(tuple([time(), where_id, sig, s_name, bytearray(data)]))

    def _disable(self):
        self.disabled = True

    def _enable(self):
        self.disabled = False
        
    def format_time(self, t):
        """
        t = time.time() -> 1475131726.001496
        format_time(t)  -> '2016.09.28 23:49:05.262983'
        """
        return strftime(self.date_f,localtime(t))+'.{:.6}'.format(str(t%1)[2:])

    def parse_time(self, s):
        """
        s               -> '2016.09.28 23:49:05.262983'
        parse_time(t)   -> 1475131726.001496
        """
        return mktime(strptime(s[:-7],self.date_f))+float('.'+s[-6:])
        
    def _format(self,t,where,sig,s_name,data):
        """
        format a trace record based on t (time) where (record type), 
        signature (stack trace), and s_name (structure to decode data with)
        """
        if ((where == 'RADIO_CMD') or
            (where == 'RADIO_RSP') or
            (where == 'RADIO_DUMP') or
            (where == 'RADIO_FRR') or
            (where == 'RADIO_GROUP')):
            s = ' {}: '.format(s_name)
            try:
                s += eval(s_name).parse(data).__repr__()
            except:
                s += data if isinstance(data, types.StringType) else binascii.hexlify(data)
        else:
            s = ' ' + data
        last_d = t-self.last_t if (self.last_t) else 0
        mark_d = t-self.mark_t if (self.mark_t) else 0
        if (mark_d):
            delta_s = ' {:.6f} {:.6f}'.format(last_d,mark_d)
        else: 
            delta_s = ' {:.6f}'.format(last_d)
        tt = self.format_time(t)
        self.index += 1
        f = '@-@{:^6}@-@ ({} {}) {} <{}>'.format(self.index,tt,delta_s,where,sig)
        return f + s

    def display(self, filter=None, count=0, begin=None, mark=None, span=0):
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
                for t,where_id,sig,s_name,data in self.rb.get():
                    where = radio_trace_ids.by_value(where_id)
                    if where in filter:
                        xb.append(n)
                    n += 1
                depth = self.rb.len() - xb.last()
            else:
                depth = count if (count < self.rb.len()) else -1
        elif (count == 0):
            count = self.size
        for t,where_id,sig,s_name,data in self.rb.peek(depth):
            where = radio_trace_ids.by_value(where_id)
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
            if ((not span_d) and (count <= 0)):
                break
            print(t,where_id,where,sig,s_name,data)
#end class

class RingBuffer:
    """
    in-memory ringbuffer used to hold the trace records. note that the
    class is modified to handle first full wrap differently
    """
    def __init__(self,size_max):
        self.max = size_max
        self.data = []
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
            n = self.max if ((n >= self.max) or (n == -1)) else n
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
def spi(t, cmd, s_name):
    t.add('RADIO_CMD', cmd, s_name, level=2)

def f1(t):
    request = change_state_cmd_s.parse('\x00' * change_state_cmd_s.sizeof())
    request.cmd = 'CHANGE_STATE'
    cmd = change_state_cmd_s.build(request)
    spi(t, cmd, change_state_cmd_s.name)

def f0(t):
    f1(t)
    t.display()

def si446xtrace_test():
    t = Trace(10)
    f0(t)
    i=time()
    s=t.format_time(i)
    o=t.parse_time(s)
    if i != o: print('si446xtrace_test fail, i should equal o')
    return i,o,s

if __name__=='__main__':
    print(si446xtrace_test())

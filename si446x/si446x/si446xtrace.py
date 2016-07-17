from si446xdef import *
from construct import *
import time

import inspect

class Trace:
    def __init__(self, size):
        self.rb = RingBuffer(size)
        self.size = size

    def add(self, where, data, s_name=None, level=1):
        where_id = radio_trace_ids.build(where)
        sig = ''
        if (level>1):
            _,_,ln_2,fn_2,_,_ = inspect.stack()[level+1]
            sig += '{}:{} -> '.format(fn_2,ln_2)
        _,_,ln_1,fn_1,_,_ = inspect.stack()[level]
        sig += '{}:{}'.format(fn_1,ln_1)
        self.rb.append([time.time(), where_id, sig, s_name, data])

    def display(self, filter=None, count=0, begin=None, mark=None, span=0):
        count = count if (count) else self.size
        last_t = 0
        mark_t = 0
        span_d = 0
        for t,where_id,sig,s_name,data in self.rb.peek(-1):
            where = radio_trace_ids.parse(where_id)
            if (span_d):
                span_d -= 1
            else:
                if (filter):
                    if (where not in filter):
                        continue
                    else:
                        span_d = span
                if ((begin) and (begin > t)):
                    continue
                if (where == mark):
                    mark_t = t
            if ((where == 'RADIO_CMD') or
                (where == 'RADIO_RSP') or
                (where == 'RADIO_FRR') or
                (where == 'RADIO_GROUP')):
                try:
                    s = eval(s_name).parse(data)
                except:
                    s = s_name + data.encode('hex')
            else:
                s = data
            last_d = t-last_t if (last_t) else 0
            mark_d = t-mark_t if (mark_t) else 0
            if (mark_d):
                delta_s = ' {:.6f} {:.6f}'.format(last_d,mark_d)
            else: 
                delta_s = ' {:.6f}'.format(last_d)
            f = '@@@@@@@ ({:^20.6f} {}) {} <{}>'
            print f.format(t,delta_s,where,sig)
            print s
            last_t = t

    def fetch(self, num):
        pass
#end class

class RingBuffer:
    def __init__(self,size_max):
        self.max = size_max
        self.data = []
    def append(self,x):
        """append an element at the end of the buffer"""
        self.data.append(x)
        if len(self.data) == self.max:
            self.cur=0
            self.__class__ = self.RingBufferFull
    def peek(self,n):
        """ return the newest elements, oldest first"""
        max = len(self.data)
        if (n == -1):
            x = 0
        else:
            x = 0 if ((n >= max) or (n == -1)) else max - n
        return self.data[x:max]
    def get(self):
        """ return a list of elements from the oldest to the newest"""
        return self.data
    class RingBufferFull:
        def __init__(self,n):
            raise "you should use RingBuffer"
        def append(self,x): 
            self.data[self.cur]=x
            self.cur=(self.cur+1) % self.max
        def peek(self, n):
            """ return the newest elements, oldest first"""
            n = self.max if ((n >= self.max) or (n == -1))  else n
            x = self.cur - n if (n < self.cur) else 0
            y = n - self.cur if (n - self.cur) > 0 else 0
            return self.data[self.max-y:self.max]+self.data[x:self.cur]
        def get(self):
            return self.data[self.cur:]+self.data[:self.cur]
#end class

# test
#
def spi(t, cmd, s_name):
    t.add('RADIO_CMD', cmd, s_name)

def f1(t):
    request = change_state_cmd_s.parse('\x00' * change_state_cmd_s.sizeof())
    request.cmd = 'CHANGE_STATE'
    cmd = change_state_cmd_s.build(request)
    spi(t, cmd, change_state_cmd_s.name)

def f0():
    t = Trace(10)
    f1(t)
    t.display()

if __name__=='__main__':
    f0()

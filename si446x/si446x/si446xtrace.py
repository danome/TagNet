from si446xdef import *
from construct import *
from time import time, ctime

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
        self.rb.append([time(), where_id, sig, s_name, data])

    def _format(self,t,where,sig,s_name,data):
        if ((where == 'RADIO_CMD') or
            (where == 'RADIO_RSP') or
            (where == 'RADIO_DUMP') or
            (where == 'RADIO_FRR') or
            (where == 'RADIO_GROUP')):
            s = ' {}: '.format(s_name)
            try:
                s += eval(s_name).parse(data).__repr__()
            except:
                s += data.encode('hex')
        else:
            s = data
        last_d = t-self.last_t if (self.last_t) else 0
        mark_d = t-self.mark_t if (self.mark_t) else 0
        if (mark_d):
            delta_s = ' {:.6f} {:.6f}'.format(last_d,mark_d)
        else: 
            delta_s = ' {:.6f}'.format(last_d)
        f = '@@@@@@@ ({} {:.6f} {}) {} <{}>'.format(ctime(t),t%1,delta_s,where,sig)
        return f + s


    def display(self, filter=None, count=0, begin=None, mark=None, span=0):
        self.last_t = 0
        self.mark_t = 0
        span_d = 0
        depth = -1
        if (count < 0):
            count = abs(count)
            if (filter):
                xb = RingBuffer(count)
                n = 0
                for t,where_id,sig,s_name,data in self.rb.get():
                    where = radio_trace_ids.parse(where_id)
                    if where in filter:
                        xb.append(n)
                    n += 1
                depth = self.rb.len() - xb.last()
            else:
                depth = count if (count < self.rb.len()) else -1
        elif (count == 0):
            count = self.size
#        print depth, count
        for t,where_id,sig,s_name,data in self.rb.peek(depth):
            where = radio_trace_ids.parse(where_id)
            if (span_d):
                span_d -= 1
            else:
                if (filter):
#                    print where, filter
                    if (where in filter):
                        if (span):
                            span_d = span-1
                    else:
                        continue
                if ((begin) and (begin > t)):
                    continue
                if (where == mark):
                    self.mark_t = t
                count -= 1
            print self._format(t,where,sig,s_name,data)
            self.last_t = t
#            print self.last_t, count, span_d
            if ((not span_d) and (count <= 0)):
                break
#end class

class RingBuffer:
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

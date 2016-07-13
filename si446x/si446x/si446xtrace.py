from si446xdef import *
from construct import *
import time

import inspect

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

class Trace:
    def __init__(self, size):
        self.rb = RingBuffer(size)
        self.size = size
    def add(self, where, data, s_name=None, level=1):
        where_id = radio_trace_ids.build(where)
        _,_,ln_1,fn_1,_,_ = inspect.stack()[level]
        _,filename,ln_2,fn_2,_,_ = inspect.stack()[level+1]
        sig = '{}:{}, {}:{} ({})'.format(ln_2,fn_2,ln_1,fn_1,filename)
        self.rb.append([time.time(), where_id, sig, s_name, data])
    def display(self, count=0):
        count = count if (count) else self.size
        for t,where_id,sig,s_name,data in self.rb.get():
            count -= 1
            if (count <= 0):
                break
            where = radio_trace_ids.parse(where_id)
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
            print '({}) {} <{}> {}'.format(t,where,sig,s)
    def fetch(self, num):
        pass

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
    def peek(self):
        """ return the oldest element"""
        return self.data[self.cur]
    def get(self):
        """ return a list of elements from the oldest to the newest"""
        return self.data
    class RingBufferFull:
        def __init__(self,n):
            raise "you should use RingBuffer"
        def append(self,x): 
            self.data[self.cur]=x
            self.cur=(self.cur+1) % self.max
        def peek(self):
            """ return the oldest element"""
            return self.data[self.cur]
        def get(self):
            return self.data[self.cur:]+self.data[:self.cur]

def save():
    (frame,filename,line_number,function_name, lines, 
     index) = inspect.getouterframes(inspect.currentframe())[1]
    s = '{}:{}({}){},{}'.format(filename, line_number, function_name, lines, index)
    print(s)
    frame,filename,line_number,function_name,lines,index = inspect.stack()[1]
    print(frame,filename,line_number,function_name,lines,index)
    frame,filename,line_number,function_name,lines,index = inspect.stack()[2]
    print(frame,filename,line_number,function_name,lines,index)

if __name__=='__main__':
    f0()

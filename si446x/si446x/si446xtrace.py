from si446xdef import *
from construct import *
import time

def Si446xFrrCtlMode_t(subcon):
    return Enum(subcon,
                RADIO_CMD              = 0,
                RADIO_RSP              = 1,
                RADIO_GROUP            = 2,
           )

class Trace:
    def __init__(self, size):
        self.rb = RingBuffer(size)
    def add(self, where, form, data):
        self.rb.append([time.time(), where, form, data])
    def display(self):
        for t,where,form,data in self.rb.get():
            if (where = 'RADIO_CMD'):
                c =radio_config_commands[form][0]
                if (c):
                    s = c.parse(data)
                else:
                    s = c.encode('hex')
            elif (where = 'RADIO_RSP'):
                c =radio_config_commands[form][0]
                if (c):
                    s = c.parse(data)
                else:
                    s = c.encode('hex')
            elif (where = 'RADIO_GROUP'):
                c =radio_config_groups[form][0]
                if (c):
                    s = c.parse(data)
                else:
                    s = c.encode('hex')
            else:
                s = data.encode('hex')
            print '({}) {}: {}'.format(t,where,s)
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



#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
from Si446xDblk import si446x_device_enable, get_dblk_bytes

def start_radio():
    return si446x_device_enable()


def read_dblk(radio, start, len):
    buf, eof = get_dblk_bytes(radio, len, start)
    print(len(buf))
    return buf, eof

if __name__ == '__main__':
    f = open('temp','w+')
    radio = start_radio()
    buf, eof = get_dblk_bytes(radio, 10000, 0)
    f.write(buf)
    f.close()

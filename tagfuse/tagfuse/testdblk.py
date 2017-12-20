#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
from Si446xDblk import si446x_device_enable, dblk_get_bytes, dblk_update_attrs, dblk_write_note

def start_radio():
    return si446x_device_enable()


def read_dblk(radio, start, len):
    buf, eof = dblk_get_bytes(radio, 0, len, start)
    return buf, eof

def read_attrs(radio):
    attrs = dict(st_mode=0, st_nlink=0, st_size=1000,
                 st_ctime=0, st_mtime=0,st_atime=0)
    return dblk_update_attrs(radio, 0, attrs)

def write_note(radio, note):
    return dblk_write_note(radio, note)

if __name__ == '__main__':
    f = open('temp','w+')
    radio = start_radio()
    buf, eof = read_dblk(radio, 10000, 0)
    f.write(buf)
    f.close()

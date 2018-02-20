#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
#from builtins import *                  # python3 types

__all__ = ['SparseFile']

print('loading sparsefile')

from binascii    import hexlify
from chest       import Chest

class SparseFile(Chest):
    '''
    Sparse file provides a large file that takes up only the
    space used by actual data written.
    '''
    def __init__(self, filename):
        print('sparsefile init', filename)
        Chest.__init__(self, path=filename)
        self.filename = filename

    def coalesce(self, offset):
        '''
        coalesce smaller blocks into larger blocks

        If two blocks are adjacent, then combine into one.
        '''
        block_list = sorted(self.keys())
        while (block_list):
            # zzz print('coalesce', block_list)
            this_pos = block_list[0]
            if this_pos < offset:
                del self[this_pos]
                continue
            if (len(block_list) == 1):
                break
            next_pos = block_list[1]
            # zzz print('coalesce', this_pos, next_pos)
            if (next_pos == this_pos + len(self[this_pos])):
                self[this_pos] = self[this_pos] + self[next_pos]
                del self[next_pos]
                del block_list[1]
            else:
                del block_list[0]

    def add_bytes(self, offset, buf):
        """
        Adds byte data to the sparsefile.

        Skip data that has already been added and fill in
        the holes by inserting new bytes.

        Returns total bytes processed.
        """
        # zzz print('add',offset, len(buf), buf)
        if len(self):
            a_s = offset
            a_e = a_s + len(buf)
            b_e = 0
            for b_s, block in self.overlay(a_s, a_e):
                b_e = b_s + len(block)
                # zzz print('add bytes', a_s, a_e, b_s, b_e, block)
                if (a_s < b_s):
                    first = a_s - offset
                    last = b_s - offset
                    self[a_s] = buf[first:last]
                    a_s = b_e
            if (b_e == 0):
                self[offset] = buf
            elif (a_e > b_e):
                first = b_e - offset
                last = a_e - offset
                self[b_e] = buf[first:last]
            self.coalesce(0)
        else:
            self[offset] = buf
        print('add bytes', len(buf), offset)
        return len(buf)

    def get_bytes_and_holes(self, offset, size):
        """
        Gets any data available in the sparsefile.

        Within the range of offset and size, if a hole is
        found, then return its starting file position and
        size. If a block of data is found, it is returned.
        The end of the previous hole/block specifies where
        the next block fits. If only a block is returned,
        then its starting position is the offset of the
        request.

        Returns list of [(start, size) | buf, ...]

        a_s and a_e   are the starting and ending offsets
                      of the requested data.
        b_s and b_e   are the starting and ending offsets
                      of the current sparsefile data block.
        a_s is advanced through the range of offset and size
        as the associated hole or data block is added to the
        rtn value.
        """
        rtn = []
        if len(self):
            a_s = offset
            a_e = b_e = offset + size
            for b_s, block in self.overlay(offset, a_e):
                b_e = b_s + len(block)
                # zzz
                print('get', a_s, a_e, b_s, b_e, hexlify(block[:24]))
                if (a_s < b_s):        # add hole if needed
                    rtn.append([a_s, b_s])
                    a_s  = b_s
                first = a_s - b_s      # add overlap data
                last  = min(a_e, b_e) - b_s
                rtn.append(block[first:last])
                a_s += last
                if (a_s > a_e):      # advanced to end of req
                    break            # done
            if (a_e > b_e):          # final hole if needed
                rtn.append([b_e, a_e])
        return rtn


    def overlay(self, start, size):
        """
        Finds the set of data blocks that are within the
        range of offset and size. From this, the list of
        blocks (bytes) and gaps (holes) can be determined.

        Returns list of indices of the blocks within the
        range.
        """
        block_list = []
        if len(self):
            a_s = start
            a_e = start + size
            for b_s in sorted(self.keys()):
                block = self[b_s]
                b_e = b_s + len(block)
                # zzz print('overlay', a_s, a_e, b_s, b_e, block)
                if (a_s > b_e): # offset after this block
                    continue    # skip
                if (a_e < b_s): # offset+size before this block
                    break       # done
                block_list.append([b_s, block]) # block overlaps
        # zzz print('block list', block_list)
        return block_list

if __name__ == '__main__':
    sf = SparseFile('foo')
    if (len(sf)):
        print('exists')
        exp = [[0, 5],
               'ABCDE10HIJKLMNO20RSTUVWXYZABCDEFGHIJKLMNOPQRS50VWXYZ',
               [57, 100]]
        assert(exp == sf.get_bytes_and_holes(0,100))
        print(sf.get_bytes_and_holes(0,100))
        sf.drop()
    else:
        sf.add_bytes(10,'10')
        assert(len(sf) == 1)
        sf.add_bytes(20,'20')
        assert(len(sf) == 2)
        sf.add_bytes(50,'50')
        sf.add_bytes(5,'ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ')
        sf.add_bytes(50,'50')
        print(sf.get_bytes_and_holes(0,100))

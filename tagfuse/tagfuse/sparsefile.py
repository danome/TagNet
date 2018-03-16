#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
#from builtins import *                  # python3 types


print('loading sparsefile')
__all__ = ['SparseFile']

from binascii    import hexlify
from chest       import Chest
from sets        import Set
from collections import defaultdict

class SparseFileException(Exception):
    '''
    This exception is raised when SparseFile detects inconsistent
    operation.
    '''
    def __init__( self, a_s, a_e, b_s, b_e):
        self.a_s = a_s if a_s is not None else 'None'
        self.a_e = a_e if a_e is not None else 'None'
        self.b_s = b_s if b_s is not None else 'None'
        self.b_e = b_e if b_e is not None else 'None'
        Exception.__init__(self,
            'SparseFile Failure: a_s: {}, a_e: {}, b_s: {}, b_e: {}'.format(
                self.a_s, self.a_e, self.b_s, self.b_e))


class SparseFile(Chest):
    '''
    Sparse file provides a large file that takes up only the
    space used by actual data written.
    '''
    def __init__(self, dirname):
        print('*** sparsefile init', dirname)
        super(SparseFile, self).__init__(path=dirname)
#        Chest.__init__(self, path=dirname)
        self.dirname = dirname
        self.counts = defaultdict(int)

    def _check_bytes(self):
        if len(self):
            for a_s in sorted(self.iterkeys()):
                block = self[a_s]
                a_e = a_s + len(block)
                set_a = Set(range(a_s, a_e))
                for b_s in sorted(self.iterkeys()):
                    if a_s == b_s:
                        continue
                    block = self[b_s]
                    b_e = b_s + len(block)
                    set_b = Set(range(b_s, b_e))
                    common = set_a.intersection(set_b)
                    if len(common):
                        # zzz
                        print("*** _check_bytes error", common)
                        raise SparseFileException(a_s, a_e, b_s, b_e)
        else:
            print("*** _check_bytes empty list")

    def _coalesce(self):
        '''
        coalesce smaller blocks into larger blocks

        Combine blocks that overlap in the sparse dictionary and
        repeat until all overlaps have been combined.

        algorithm:
        1 first sort the list of keys in the sparse dictionary,
          we want to process in ascending order to reduce the
          number of test conditions.
        2 next, start with the first two block in the list.
        3 compare the two blocks (call them first and second)
          i)   if first block ends before the second block begins,
               first block is no longer of interest, replace it
               with the second block
          ii)  else if first block is strict superset of the second,
               discard second block
          iii) else part of first block overlaps with the beginning
               of the second block, combine the two blocks into one
               which becomes the new first block. discard the
               the second block
        4 get new second block from the list and repeat steps 3-4
          until no more blocks in the list
        '''
        # list is sorted, so b_s (second block) can never be less
        # than a_s (first block) in the comparisons
        # if self.counts['coalese_count'] % 100:
        print('*** {} sparsefile, cur/max number of blocks: {}/{}, max block size: {}'.format(
                self.counts['coalesce_count'],
                len(self), self.counts['max_block_count'],
                self.counts['max_block_size'],
            ))
        block_list = sorted(self.iterkeys())
        if block_list is None:
            return
        if (len(self) > self.counts['max_block_count']):
            self.counts['max_block_count'] = len(self)
        self.counts['coalesce_count'] += 1
        a_s   = block_list.pop(0)
        a_blk = self[a_s]
        a_e   = a_s + len(a_blk)
        while (len(block_list)):
            if (len(a_blk) > self.counts['max_block_size']):
                self.counts['max_block_size'] = len(a_blk)
            # zzz print('*** coalesce block_list', block_list)
            # first time only, start and end addresses for a_blk
            # start and end address for b_blk
            b_s   = block_list.pop(0)
            b_blk = self[b_s]
            b_e   = b_s + len(b_blk)
            # zzz print('*** _coalesce loop: a_s: {}, a_e: {}, b_s: {}, b_e: {}'.format(
            # zzz    a_s, a_e, b_s, b_e))
            # case (3.i) first ends before second begins
            if (a_e < b_s):
                # zzz print('*** coalesce skip to next')
                # no more overlap, move on starting with b_blk
                a_s   = b_s
                a_blk = b_blk
                a_e   = b_e
            # case (3.ii) first subsumes second
            elif (a_e >= b_e):
                # zzz print("coalesce replace", a_s, a_e, b_s, b_e)
                del self[b_s]
            # case (3.iii) first overlaps with beginning of second
            elif (a_e < b_e):
                # zzz print("coalesce combine",
                # zzz       len(a_blk), hexlify(a_blk), len(b_blk), hexlify(b_blk))
                # slice the first part of a_blk up to the overlap
                # with b_blk and then combine with b_blk
                new_block = a_blk[:b_s-a_s]
                new_block.extend(b_blk)
                # zzz print("coalesce combine new", len(new_block), hexlify(new_block))
                # replace old a_blk with new_block and delete b_blk.
                self[a_s] = a_blk = new_block
                a_e = b_e
                del self[b_s]
            # not expected
            else:
                raise SparseFileException(a_s, b_s, a_e, b_e)
        # self._check_bytes()

    def add_bytes(self, offset, buf):
        """
        Adds byte data to the sparsefile.

        Skip data that has already been added and fill in
        the holes by inserting any new bytes.

        Returns total bytes processed (added + existing).
        """
        if len(buf) == 0:
            return 0

        # self._check_bytes()
        # zzz print('*** add_bytes, offset/len', offset, len(buf))
        try: # replace if offset exists and buffer is longer
            if len(self[offset]) < len(buf):
                self[offset] = buf
        except KeyError:
            self[offset] = buf  # otherwise add new entry
        self._coalesce()
        # self._check_bytes()
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
        # self._check_bytes()
        rtn = []
        if len(self):
            a_s = offset
            a_e = b_e = offset + size
            for b_s, block in self._overlay(a_s, a_e):
                b_e = b_s + len(block)
                # zzz print('*** get_bytes/holes', a_s, a_e, b_s, b_e, hexlify(block[:24]))
                if (a_s < b_s):        # add hole if needed
                    rtn.append([a_s, b_s])
                    a_s  = b_s
                first = a_s - b_s      # add overlap data
                last  = min(a_e, b_e) - b_s
                chunk = block[first:last]
                rtn.append(chunk)
                a_s += len(chunk)
                #a_s += last
                if (a_s > a_e):        # done
                    break
            if (a_e > b_e):            # final hole if needed
                rtn.append([b_e, a_e])
        # self._check_bytes()
        # zzz print(rtn)
        return rtn


    def _overlay(self, a_s, a_e):
        """
        Finds the set of data blocks that are within the range
        of starting (a_s) and ending (a_e) byte positions.
        This information is used by the caller determine the
        list of blocks (bytes) and gaps (holes).

        Returns list of (offset, block) tuples of the blocks
        within the range.
        """
        # self._check_bytes()
        block_list = []
        if len(self):
            for b_s in sorted(self.iterkeys()):
                block = self[b_s]
                b_e = b_s + len(block)
                # zzz print('*** _overlay', a_s, a_e, b_s, b_e, len(block))
                if (a_s >= b_e): # offset after this block
                    continue    # skip
                if (b_s > a_e): # offset+size before this block
                    break       # done
                block_list.append((b_s, block)) # block overlaps
        # zzz print('*** overlay block list', len(block_list))
        # self._check_bytes()
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

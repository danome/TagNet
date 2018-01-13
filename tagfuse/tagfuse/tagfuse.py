#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging
import os
from collections import defaultdict, OrderedDict
from errno import ENOENT, ENODATA
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from Si446xFile import si446x_device_enable

from taghandlers import *

if not hasattr(__builtins__, 'bytes'):
    bytes = str

class TagFuse(LoggingMixIn, Operations):
    '''
    Exposes Tag SD Storage as Fuse Filesystem

    Both buffered and direct_io operation is supported

    Direct_io read is accessed in the following way:
      f = os.open('foo/dblk/0',  os.O_DIRECT | os.O_RDONLY)
      buf = os.read(f, 10)
      os.lseek(f, fpos, 0)
      fpos = os.lseek(f, 0, 1)  # returns current file position
    '''

    def __init__(self):
        self.create_count = 0
        self.open_count = 0
        self.start = time()
        self.radio = si446x_device_enable()
        self.tag_tree = DirHandler(OrderedDict([
            ('',         FileHandler(S_IFDIR, 0o751, 4)),
            ('dblk',     DirHandler(OrderedDict([
                ('',         FileHandler(S_IFDIR, 0o751, 4)),
                ('byte',     DirHandler(OrderedDict([
                    ('',          FileHandler(S_IFDIR, 0o751, 4)),
                    ('0',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)), ]))),
                ('note',     DblkIONoteHandler(self.radio, S_IFREG, 0o220, 1)),
            ]))),
            ('panic',    DirHandler(OrderedDict([
                ('',         FileHandler(S_IFDIR, 0o751, 3)),
                ('byte',     DirHandler(OrderedDict([
                    ('',          FileHandler(S_IFDIR, 0o751, 35)),
                    ('0',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('1',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('2',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('3',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('4',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('5',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('6',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('7',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('8',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('9',         ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('10',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('11',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('12',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('13',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('14',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('15',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('16',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('17',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('18',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('19',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('20',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('21',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('22',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('23',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('24',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('25',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('26',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('27',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('28',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('29',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('30',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)),
                    ('31',        ByteIOFileHandler(self.radio, S_IFREG, 0o444, 1)), ]))),
            ]))),
        ]))

    def path2list(self, path):
        path = os.path.abspath(os.path.realpath(path))
        return path.split('/')[1:]

    def LocateNode(self, path):
        if (path == '/'):
            return self.tag_tree
        return self.tag_tree.traverse(self.path2list(path), 0)

    def chmod(self, path, mode):
        raise FuseOSError(ENOENT)
        return 0

    def chown(self, path, uid, gid):
        raise FuseOSError(ENOENT)

    def create(self, path, mode):
        raise FuseOSError(ENOENT)
        self.create_count += 1
        return 0
#        return self.fd # raw_io doesn't expect a fileno

    def fsync(self, path, datasync, fip):
        raise FuseOSError(ENOENT)
        print(path, datasync, fip)
        # zzz use this to trigger tag to search for sync record
        return 0

    def getattr(self, path, fh=None):
        handler = self.LocateNode(path)
        try:
            return handler.getattr(self.path2list(path), update=True)
        except:
            raise FuseOSError(ENOENT)

    def getxattr(self, path, name, position=0):
        handler = self.LocateNode(path)
        try:
            attrs = handler.getattr(self.path2list(path))
            return attrs.get('attrs', {})[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        handler = self.LocateNode(path)
        try:
            attrs = handler.getattr(self.path2list(path))
            return attrs.get('attrs', {}).keys()
        except:
            raise FuseOSError(ENOENT)

    def mkdir(self, path, mode):
        raise FuseOSError(ENOENT)

    def open(self, path, flags):
        self.open_count += 1
        return 0
#        return self.fd # raw_io doesn't expect a fileno

    def read(self, path, size, offset, fh):
        handler = self.LocateNode(path)
        try:
            return handler.read(self.path2list(path), size, offset)
        except:
            raise FuseOSError(ENOENT)

    def readdir(self, path, fh):
        handler = self.LocateNode(path)
        try:
            return handler.readdir(self.path2list(path))
        except:
            return []

    def readlink(self, path):
        raise FuseOSError(ENOENT)

    def removexattr(self, path, name):
        handler = self.LocateNode(path)
        try:
            attrs = handler.getttr(self.path2list(path))
            del attrs.get('attrs', {})[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        raise FuseOSError(ENOENT)

    def rmdir(self, path):
        raise FuseOSError(ENOENT)

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        handler = self.LocateNode(path)
        try:
            attrs = handler.getattr(self.path2list(path))
            attrs[name] = value
        except:
            raise FuseOSError(ENOENT)

    def statfs(self, path):
        '''
        struct statvfs {
               unsigned long  f_bsize;    /* Filesystem block size */
               unsigned long  f_frsize;   /* Fragment size */
               fsblkcnt_t     f_blocks;   /* Size of fs in f_frsize units */
               fsblkcnt_t     f_bfree;    /* Number of free blocks */
               fsblkcnt_t     f_bavail;   /* Number of free blocks for
                                             unprivileged users */
               fsfilcnt_t     f_files;    /* Number of inodes */
               fsfilcnt_t     f_ffree;    /* Number of free inodes */
               fsfilcnt_t     f_favail;   /* Number of free inodes for
                                             unprivileged users */
               unsigned long  f_fsid;     /* Filesystem ID */
               unsigned long  f_flag;     /* Mount flags */
               unsigned long  f_namemax;  /* Maximum filename length */
           };
        '''
        return dict(f_bsize=512, f_frsize=512, f_blocks=0, f_bavail=0)

    def symlink(self, target, source):
        raise FuseOSError(ENOENT)

    def truncate(self, path, length, fh=None):
        handler = self.LocateNode(path)
        try:
            return handler.truncate(self.path2list(path), length)
        except:
            raise FuseOSError(ENOENT)

    def unlink(self, path):
        raise FuseOSError(ENOENT)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        handler = self.LocateNode(path)
        try:
            meta.attrs['st_atime'] = atime
            meta.attrs['st_mtime'] = mtime
        except:
            pass

    def write(self, path, data, offset, fh):
        handler = self.LocateNode(path)
        try:
            return handler.write(self.path2list(path), data, offset)
        except:
            return 0

def TagStorage(argv):
    options = {'max_write':     0,
               'max_read':      512,
               'max_readahead': 8192,
               'kernel_cache':  True,
               'direct_io':     True,
    }
    # zzz
    logging.basicConfig(level=logging.INFO)
    # zzz logging.basicConfig(level=logging.DEBUG) # output FUSE related debug info
    fuse = FUSE(TagFuse(), argv[1], nothreads=True, raw_fi=True, foreground=True, **options)

if __name__ == '__main__':
    from sys import argv
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)
    TagStorage(argv)

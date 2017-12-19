#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

from collections import defaultdict, OrderedDict
from errno import ENOENT, ENODATA
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from tagagg import *

from Si446xDblk import si446x_device_enable, dblk_get_bytes, dblk_update_attrs

if not hasattr(__builtins__, 'bytes'):
    bytes = str

class node_details(object):
    def __init__(self, ntype, mode, nlinks):
        self.attrs = dict(st_mode=(ntype | mode), st_nlink=nlinks,
                          st_size=4096, st_ctime=time(), st_mtime=time(),
                          st_atime=time())
        self.data = bytes()


dblk_tree = aggie(OrderedDict([
    ('',         atom(node_details(S_IFDIR, 0o755, 4))),
    ('0',        atom(node_details(S_IFREG, 0o666, 1))),
    ('1',        atom(node_details(S_IFREG, 0o666, 1))),
]))

panic_tree = aggie(OrderedDict([
    ('',         atom(node_details(S_IFDIR, 0o755, 4))),
    ('0',        atom(node_details(S_IFREG, 0o666, 1))),
    ('1',        atom(node_details(S_IFREG, 0o666, 1))),
]))

file_tree = aggie(OrderedDict([
    ('',         atom(node_details(S_IFDIR, 0o755, 4))),
    ('dblk',     dblk_tree),
    ('panic',    panic_tree),
]))

class TagFuse(LoggingMixIn, Operations):
    '''
    Exposes Tag SD Storage as Fuse Filesystem
    '''

    def __init__(self):
        self.fd = 0
        self.start = time()
        self.radio = si446x_device_enable()

    def chmod(self, path, mode):
        return 0

    def chown(self, path, uid, gid):
        pass

    def create(self, path, mode):
        self.fd += 1
        return self.fd

    def fsync(self, path, datasync, fip):
        print(path, datasync, fip)
        # zzz add resync command (next word/sector)
        return 0

    def getattr(self, path, fh=None):
        meta = get_meta(file_tree, path)
        if (meta):
            if ((meta.attrs['st_mode'] & S_IFREG) == S_IFREG):
                return dblk_update_attrs(self.radio, meta.attrs)
            return meta.attrs
        raise FuseOSError(ENOENT)

    def getxattr(self, path, name, position=0):
        meta = get_meta(file_tree, path)
        if (meta):
            try:
                return meta.attrs.get('attrs', {})[name]
            except KeyError:
                return ''       # Should return ENOATTR
        return ''

    def listxattr(self, path):
        meta = get_meta(file_tree, path)
        if (meta):
            return meta.attrs.get('attrs', {}).keys()
        raise FuseOSError(ENOENT)

    def mkdir(self, path, mode):
        raise FuseOSError(ENOENT)

    def open(self, path, flags):
        self.fd += 1
        return 0
#        return self.fd # direct_io doesn't expect a fileno

    def read(self, path, size, offset, fh):
        meta = get_meta(file_tree, path)
        if (meta):
            buf, eof = dblk_get_bytes(self.radio, size, offset)
#            print(len(buf),eof)
            if (eof):
                raise FuseOSError(ENODATA)
#            return 'this string works'
            return str(buf)
        raise FuseOSError(ENODATA)

    def readdir(self, path, fh):
        dir_list = get_dir_names(file_tree, path)
        if (dir_list):
            return ['.', '..'] + dir_list
        return []

    def readlink(self, path):
        meta = get_meta(file_tree, path)
        if (meta):
            return meta.attrs
        raise FuseOSError(ENOENT)

    def removexattr(self, path, name):
        meta = get_meta(file_tree, path)
        try:
            del meta.attrs.get('attrs', {})[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        pass

    def rmdir(self, path):
        pass

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        meta = get_meta(file_tree, path)
        try:
            meta.attrs[name] = value
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
#        path = os.path.abspath(os.path.realpath(path))
#        print(path)
#        stv = os.statvfs(path)
#        if (stv):
#            stv['f_bsize']  = 512
#            stv['f_blocks'] = 1
#            stv['f_bavail'] = 200
#        ret = dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
#                                                        'f_blocks', 'f_bsize',
#                                                        'f_favail', 'f_ffree',
#                                                        'f_files', 'f_flag',
#                                                        'f_frsize', 'f_namemax'))
#        stv['f_bsize']  = 512
#        stv['f_blocks'] = 1
#        stv['f_bavail'] = 200
#        print(ret)
#        return ret

    def symlink(self, target, source):
        pass

    def truncate(self, path, length, fh=None):
        pass

    def unlink(self, path):
        pass

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        meta = get_meta(file_tree, path)
        if (meta):
            meta.attrs['st_atime'] = atime
            meta.attrs['st_mtime'] = mtime

    def write(self, path, data, offset, fh):
        meta = get_meta(file_tree, path)
        if (meta):
            meta.data += data
            meta.attrs['st_size'] = len(meta.data)
        return len(data)

if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    options = {'max_write':     0,
               'max_read':      512,
               'max_readahead': 1024,
               'kernel_cache':  True,
               'direct_io':     True,
    }

    logging.basicConfig(level=logging.INFO)
    # zzz logging.basicConfig(level=logging.DEBUG) # output FUSE related debug info
    fuse = FUSE(TagFuse(), argv[1], nothreads=True, raw_fi=True, foreground=True, **options)

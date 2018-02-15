#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
#from builtins import *                  # python3 types

print('tagfuse','starting')

__all__ = ['TagStorage',
           'TagFuse']
import os
import sys
reload(sys)
#sys.setdefaultencoding('utf-8')
print('default encoding', sys.getdefaultencoding())

import logging
from collections import defaultdict, OrderedDict
from errno import ENOENT, ENODATA
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time
from pwd import getpwnam

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# zzz print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [basedir,
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print '\n'.join(sys.path)

from radioutils  import radio_start, path2list
from taghandlers import *
from TagFuseTree import TagFuseRootTree

#if not hasattr(__builtins__, 'bytes'):
#    bytes = str

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
        self.radio = None
        self.tag_tree =  None
        # zzz print(self.tag_tree)

        #uid, gid, pid = fuse_get_context()
        print('tagfuse context', fuse_get_context())
        print(os.getuid(), os.geteuid())
        print(os.getgid(), os.getegid())

        self.uid = os.getuid()
        self.gid = os.getgid()

        #clear up any possible env var diffs
        os.environ['USER'] = 'pi'
        os.environ['USERNAME'] = 'pi'
        os.environ['LOGNAME'] = 'pi'

    def LocateNode(self, path):
        if (path == '/'):
            print('located root')
            return self.tag_tree
        return self.tag_tree.traverse(path2list(path), 0)

    def DeleteNode(self, path, node):
        pass

    def chmod(self, path, mode):
        raise FuseOSError(ENOENT)
        return 0

    def chown(self, path, uid, gid):
        raise FuseOSError(ENOENT)

    def create(self, path, mode, fh):
        base, name = os.path.split(path)
        handler = self.LocateNode(base)
        print('fuse create', base, name, handler)
        # try:
        if (handler):
            return handler.create(path2list(path), mode)
        # except:
        #    raise FuseOSError(ENOENT)
        #    return 0       # raw_io doesn't expect a fileno
        #    return self.fd

    def destroy(self, path):
        print('tagfuse destroy')
        return None

    def fsync(self, path, datasync, fip):
        print(path, datasync, fip)
        raise FuseOSError(ENOENT)
        # zzz use this to trigger tag to search for sync record
        return 0

    def flush(self, path, fh):
        handler = self.LocateNode(path)
        if (handler):
            return handler.flush(path2list(path))
        raise FuseOSError(ENOENT)

    def getattr(self, path, fh=None):
        handler = self.LocateNode(path)
        try:
            return handler.getattr(path2list(path), update=True)
        except AttributeError:
            raise FuseOSError(ENOENT)

    def getxattr(self, path, name, position=0):
        handler = self.LocateNode(path)
        try:
            attrs = handler.getattr(path2list(path))
            return attrs.get('attrs', {})[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def init(self, path):
        self.radio = radio_start()
        self.tag_tree = TagFuseRootTree(self.radio)
        return None

    def link(self, link_name, target):
        base, name = os.path.split(link_name)
        print('tagfuse.link',link_name, target, base, name)
        handler = self.LocateNode(base) # parent node creates context
        if (handler):
            return handler.link(link_name, target)
        raise FuseOSError(ENOENT)

    def listxattr(self, path):
        handler = self.LocateNode(path)
        if (handler):
            attrs = handler.getattr(path2list(path))
            return attrs.get('attrs', {}).keys()
        raise FuseOSError(ENOENT)

    def mkdir(self, path, mode):
        raise FuseOSError(ENOENT)

    def open(self, path, flags):
        self.open_count += 1
        return 0
#        return self.fd # raw_io doesn't expect a fileno

    def opendir(self, path):
        return 0

    def read(self, path, size, offset, fh):
        handler = self.LocateNode(path)
        return (str(handler.read(path2list(path), size, offset)))

    def readdir(self, path, fh):
        handler = self.LocateNode(path)
        # zzz print('readdir, handler type:{}, len: {}'.format(type(handler), len(handler)))
        dir_list = handler.readdir(path2list(path))
        if dir_list:
            return dir_list
        else:
            return ['.', '..']

    def readlink(self, path):
        raise FuseOSError(ENOENT)

    def release(self, path, fh):
        print('tag release')
        handler = self.LocateNode(path)
        try:
            base, name = os.path.split(path)
            ret_val = handler.release(path2list(path))
            dhandler = self.LocateNode(path2list(base))
            dhandler.release(path2list(path))
            return ret_val
        except:
            return 0

    def releasedir(self, path, fh):
        return 0

    def removexattr(self, path, name):
        handler = self.LocateNode(path)
        try:
            attrs = handler.getttr(path2list(path))
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
            attrs = handler.getattr(path2list(path))
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

    def symlink(self, link_name, target):
        handler = self.LocateNode(link_name)
        if (handler):
            return handler.symlink(link_name, target)
        raise FuseOSError(ENOENT)

    def truncate(self, path, length, fh=None):
        handler = self.LocateNode(path)
        if (handler):
            return handler.truncate(path2list(path), length)
        raise FuseOSError(ENOENT)

    def unlink(self, path):
        base, name = os.path.split(path)
        handler = self.LocateNode(path)
        if (handler) and (handler.unlink(path2list(path)) == 0):
            dirhandler = self.LocateNode(base)
            if (dirhandler):
                return (dirhandler.unlink(path2list(path)))
        raise FuseOSError(ENOENT)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        handler = self.LocateNode(path)
        if isinstance(handler, DirHandler):
            attrs = handler['']
        else:
            attrs = handler
        try:
            attrs['st_atime'] = atime
            attrs['st_mtime'] = mtime
        except:
            pass

    def write(self, path, data, offset, fh):
        handler = self.LocateNode(path)
        try:
            return handler.write(path2list(path), data, offset)
        except:
            return 0


def TagStorage(args):
    options = {'max_write':     0,
               'max_read':      512,
               'max_readahead': 8192,
               'kernel_cache':  True,
               'direct_io':     True,
    }
    # zzz logging.basicConfig(level=logging.INFO)
    # zzz
    logging.basicConfig(level=logging.DEBUG) # output FUSE related debug info
    fuse = FUSE(TagFuse(), args.mountpoint, nothreads=True, raw_fi=True, foreground=True, **options)

if __name__ == '__main__':
    import tagfuseargs
    TagStorage(tagfuseargs.parseargs(argv))

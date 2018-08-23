#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
#from builtins import *                  # python3 types

# zzz print('*** tagfuse.py','starting')

__all__ = ['TagStorage',
           'TagFuse',]

import os
import sys
import structlog
logger = structlog.getLogger('fuse.log-mixin.' + __name__)
toplog = logger.bind(scope='global')


#sys.setdefaultencoding('utf-8')
# zzz print('default encoding', sys.getdefaultencoding())

from collections import defaultdict, OrderedDict
from errno import ENOENT, ENODATA, EPERM
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
    add_dirs = [
        basedir,
        os.path.join(basedir, 'tagfuse'),
        os.path.join(basedir, '../si446x'),
        os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('** tagfuse path:', __file__, basedir)
    # zzz print('\n'.join(sys.path))

try:
    from radioutils  import path2list
except ImportError:
    from tagfuse.radioutils  import path2list

try:
    from TagFuseTree import TagFuseRootTree, TagFuseTagTree
except ImportError:
    from tagfuse.TagFuseTree import TagFuseRootTree, TagFuseTagTree

from si446x import Si446xRadio
from si446x import get_config_wds, get_name_wds, wds_default_config

# fix bug with utf-8 encoding after loading Python sys package
reload(sys)

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
        self.tree_root =  None
        # zzz print(self.tree_root)

        #uid, gid, pid = fuse_get_context()
        toplog.debug('tagfuse context {}'.format(fuse_get_context()))

        # zzz print(os.getuid(), os.geteuid())
        # zzz print(os.getgid(), os.getegid())
        self.uid = os.getuid()
        self.gid = os.getgid()

        #clear up any possible env var diffs
        os.environ['USER'] = 'pi'
        os.environ['USERNAME'] = 'pi'
        os.environ['LOGNAME'] = 'pi'

    def LocateNode(self, path):
        path_list = path2list(path)
        if (path == '/'):
            return self.tree_root, path_list
        return self.tree_root.traverse(self.tree_root, path_list, 0)

    def DeleteNode(self, path, node):
        pass

    def chmod(self, path, mode):
        raise FuseOSError(ENOENT)
        return 0

    def chown(self, path, uid, gid):
        raise FuseOSError(ENOENT)

    def create(self, path, mode, fh):
        base, name = os.path.split(path)
        dirhandler, path_list = self.LocateNode(base)
        print('** fuse create', base, name, dirhandler)
        # try:
        if (dirhandler):
            path_list.append(name)
            return dirhandler.create(path_list, mode)

    def destroy(self, path):
        print('** tagfuse destroy')
        return None

    def fsync(self, path, datasync, fip):
        print('** fsync', path, datasync, fip)
        raise FuseOSError(ENOENT)
        # zzz use this to trigger tag to search for sync record
        return 0

    def flush(self, path, fh):
        handler, path_list = self.LocateNode(path)
        if (handler):
            return handler.flush(path_list)
        raise FuseOSError(ENOENT)

    def getattr(self, path, fh=None):
        print('** getattr: path {}'.format(path))
        handler, path_list = self.LocateNode(path)
        # zzz print('** getattr: pathlist: {}'.format(path_list))
        try:
            return handler.getattr(path_list, update=True)
        except AttributeError:
            raise FuseOSError(ENOENT)

    def getxattr(self, path, name, position=0):
        handler, path_list = self.LocateNode(path)
        try:
            attrs = handler.getattr(path_list)
            return attrs.get('attrs', {})[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def init(self, path):
        '''
        start up the radio with selected configuration settings and
        then initialize the tag fuse class tree
        '''
        self.radio=Si446xRadio(0)
        if (self.radio == None):
            raise RuntimeError('radio_start: could not instantiate radio')
        self.radio.unshutdown()
        wds_default_config(0) # force alternate default config
        self.radio.write_config()
        self.radio.config_frr()
        # RPi specific config
        self.radio.set_property('PKT', 0x0b, '\x28\x28') # tx/rx threshold
        self.radio.set_property('PREAMBLE', 0, '\x40')   # long preamble
        self.tree_root = TagFuseRootTree(self.radio)
        return None

    def link(self, link, target):
        print('** tagfuse.link', link, target)
        # make sure target exists
        target_handler, target_list = self.LocateNode(target)
        if (not target_handler):
            print('** tagfuse.link target doesnt exist')
            raise FuseOSError(ENOENT)
        link_base, link_name = os.path.split(link)
        # make sure version matches
        target_base, target_name = os.path.split(target)
        if (link_name != target_name):
            print('** tagfuse.link names dont match')
            raise FuseOSError(EPERM)
        # link directory handler creates context for linked file
        link_handler, link_list = self.LocateNode(link_base)
        if (link_handler):
            return link_handler.link(link_list, target_list)
        print('** tagfuse.link link doesnt exist')
        raise FuseOSError(ENOENT)

    def listxattr(self, path):
        handler, path_list = self.LocateNode(path)
        if (handler):
            attrs = handler.getattr(path_list)
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
        handler, path_list = self.LocateNode(path)
        return (str(handler.read(path_list, size, offset)))

    def readdir(self, path, fh):
        handler, path_list = self.LocateNode(path)
        # zzz print('readdir, handler type:{}, len: {}'.format(type(handler), len(handler)))
        dir_list = handler.readdir(path_list, self.tree_root, TagFuseTagTree)
        if dir_list:
            return dir_list
        else:
            return ['.', '..']

    def readlink(self, path):
        raise FuseOSError(ENOENT)

    def release(self, path, fh):
        print('** tag release')
        handler, path_list = self.LocateNode(path)
        base, name  = os.path.split(path)
        ret_val     = handler.release(path_list)
        dhandler, _ = self.LocateNode(base)
        try:
            dhandler.release(path_list)
        except AttributeError:
            pass
        return ret_val

    def releasedir(self, path, fh):
        return 0

    def removexattr(self, path, name):
        handler, path_list = self.LocateNode(path)
        try:
            attrs = handler.getttr(path_list)
            del attrs.get('attrs', {})[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        raise FuseOSError(ENOENT)

    def rmdir(self, path):
        raise FuseOSError(ENOENT)

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        handler, path_list = self.LocateNode(path)
        try:
            attrs = handler.getattr(path_list)
            attrs[name] = value
        except KeyError:
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
        raise FuseOSError(ENOENT)

    def truncate(self, path, length, fh=None):
        handler, path_list = self.LocateNode(path)
        if (handler):
            return handler.truncate(path_list, length)
        raise FuseOSError(ENOENT)

    def unlink(self, path):
        base, name = os.path.split(path)
        handler, path_list = self.LocateNode(path)
        if (handler) and (handler.unlink(path_list) == 0):
            dirhandler, _ = self.LocateNode(base)
            if (dirhandler):
                return (dirhandler.unlink(path_list))
        raise FuseOSError(ENOENT)

    def utimens(self, path, times=None):
        now = time()
        handler, path_list = self.LocateNode(path)
        if (handler):
            return handler.utimens(path_list,
                                   times if times else (now, now))
        return 0

    def write(self, path, data, offset, fh):
        handler, path_list = self.LocateNode(path)
        return handler.write(path_list, data, offset)

def TagStorage(args):
    options = {'max_write':     0,
               'max_read':      256,
               'max_readahead': 8192,
               'kernel_cache':  True,
               'direct_io':     True,
    }
    fuse = FUSE(TagFuse(),
                args.mountpoint,
                nothreads=True,
                raw_fi=True,
                foreground= not args.background,
                **options)

if __name__ == '__main__':
    import tagfuseargs
    TagStorage(tagfuseargs.process_cmd_args())

toplog.debug('initiialization complete')

#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
#from builtins import *                  # python3 types

__all__ = ['FileHandler',
           'TestBaseHandler',
           'TestEchoHandler',
           'TestOnesHandler',
           'TestZerosHandler',
           'TestSumHandler',
           'ByteIOFileHandler',
           'SparseIOFileHandler',
           'ImageIOFileHandler',
           'SimpleRecHandler',
           'DirHandler',
           'PollNetDirHandler',
           'ImageDirHandler',
           'SysActiveDirHandler',
           'SysBackupDirHandler',
           'SysGoldenDirHandler',
           'SysNibDirHandler',
           'SysRunningDirHandler',
]

import os
import sys

from sets import Set

import logging

from   collections   import defaultdict, OrderedDict
from   errno         import ENOENT, ENODATA, EEXIST, EPERM, EINVAL, EIO
from   stat          import S_IFDIR, S_IFLNK, S_IFREG
from   time          import time
from   sets          import Set
from   fuse          import FuseOSError
from   binascii      import hexlify

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('\n'.join(sys.path))

from tagfuse.radiofile   import file_get_bytes, file_put_bytes, file_update_attrs
from tagfuse.radioimage  import im_put_file, im_get_file, im_delete_file, im_close_file
from tagfuse.radioimage  import im_get_dir, im_set_version
from tagfuse.radioutils  import path2list
from tagfuse.tagfuseargs import get_cmd_args
from tagfuse.sparsefile  import SparseFile
#from tagfuse.TagFuseTree import TagFuseTagTree

from tagnet              import tlv_errors

base_value = 0

def new_inode():
    global base_value
    base_value += 1
    return base_value

def default_file_attrs(ntype, mode, nlinks, size):
        return dict(st_mode=(ntype | mode),
                    st_nlink=nlinks,
                    st_uid=os.getuid(),
                    st_gid=os.getgid(),
                    st_blksize=512,
                    st_size=size,
                    st_ctime=time(),
                    st_mtime=time(),
                    st_atime=time())


class FileHandler(OrderedDict):
    '''
    Base File Handler class

    Performs all FUSE file related  operations.
    '''
    def __init__(self, ntype, mode, nlinks):
        a_dict = default_file_attrs(ntype,
                                    mode,
                                    nlinks,
                                    0)
        super(FileHandler, self).__init__(a_dict)
        self.inode = new_inode();

    def __len__(self):
        return 1

    def getattr(self, path_list, update=False):
        return self

    def flush(self, path_list):
        return 0

    def link(self, link_name, target): # hard link
        raise FuseOSError(EPERM)

    def read(self, path_list, size, offset):
        raise FuseOSError(ENODATA)

    def release(self, path_list):      # close
        return 0

    def truncate(self, path_list, length):
        return 0

    def unlink(self, path_list):       # delete
        raise FuseOSError(EPERM)

    def write(self, path_list, buf, offset):
        raise FuseOSError(EPERM)


class ByteIOFileHandler(FileHandler):
    '''
    Byte IO File Handler class

    Performs Byte IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(ByteIOFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def read(self, path_list, size, offset):
        # zzz print('byte io read, size: {}, offset: {}'.format(size, offset))
        buf, eof = file_get_bytes(self.radio,
                                  path_list,
                                  size,
                                  offset)
        # zzz print('read',len(buf),eof)
        return buf

    def getattr(self, path_list, update=False):
        if (update):
            self = file_update_attrs(self.radio, path_list, self)
        return self

    def write(self, path_list, buf, offset):
        # zzz print('byte io write, size: {}, offset: {}'.format(len(buf), offset))
        return file_put_bytes(self.radio,
                        path_list,
                        buf,
                        offset)


class SparseIOFileHandler(ByteIOFileHandler):
    '''
    '''
    def __init__(self, *args, **kwargs):
        super(SparseIOFileHandler, self).__init__(*args, **kwargs)
        self.sparse = None
        print("sparse handler init:", get_cmd_args().sparse_dir)

    def _open_sparse(self, fpath):
        # zzz print("*** _open_sparse input: ", self.sparse, get_cmd_args().disable_sparse)
        if self.sparse is not None or get_cmd_args().disable_sparse:
            # zzz print("*** _open_sparse: early exit")
            return
        sparse_filename = os.path.join(
            get_cmd_args().sparse_dir,
            '_'.join(fpath))
        # zzz print("*** _open_sparse filename: {}, object:  {} ".format(sparse_filename, self.sparse))
        try:
            self.sparse = SparseFile(sparse_filename)
        except:
            print("sparse handler exception")
            raise
        items = sorted(self.sparse.items())
        if items:
            offset, block = items[-1]
            if self['st_size'] < (offset + len(block)):
                self['st_size'] = offset + len(block)
        # zzz print("*** _open_sparse output: ", len(items), self.sparse)

    def _get_sparse(self, offset, size):
        if self.sparse is None or get_cmd_args().disable_sparse_read:
            return []
        return self.sparse.get_bytes_and_holes(offset, size)

    def _add_sparse(self, offset, buf):
        if self.sparse is not None:
            return self.sparse.add_bytes(offset, buf)
        return len(buf) # acknowledge but ignore data

    def _close_sparse(self):
        if self.sparse is not None:
            self.sparse.flush()

    def _delete_sparse(self):
        if self.sparse is not None:
            self.sparse.clear()
            self.sparse.flush()
            self.sparse.drop()
            self.sparse = None
            self['st_size'] = 0
            print("*** _delete_sparse deleted")

    def flush(self, *args, **kwargs):
        print('*** sparse IO flush', args[0])
        self._close_sparse()
        super(SparseIOFileHandler, self).flush(*args, **kwargs)
        return 0

    def getattr(self, *args, **kwargs):
        # zzz print('*** sparse IO getattr', args[0])
        self._open_sparse(args[0])
        super(SparseIOFileHandler, self).getattr(*args, **kwargs)
        return self

    def read(self, path_list, size, offset):
        # zzz print('*** sparse IO read, offset: {}, size: {}, eof: {}'.format(
        #    offset, size, self['st_size']))
        # refresh the file size if seeking beyond our current size
        if offset >= self['st_size']:
            super(SparseIOFileHandler, self).getattr(path_list, update=True)
        if offset >= self['st_size']:
            raise FuseOSError(ENODATA)
        try:
            self._open_sparse(path_list)
        except:
            raise
        retbuf = bytearray()
        size = min(size, self['st_size'] - offset)
        work_list = self._get_sparse(offset, size)
        if (work_list):
            for item in work_list:
                if isinstance(item, tuple) or \
                   isinstance(item, list):
                    first, last = item
                    last = min(last, self['st_size'])
                    xbuf, eof  = file_get_bytes(self.radio, path_list,
                                                last-first, first)
                    if (xbuf):
                        retbuf.extend(xbuf)
                        self._add_sparse(first, xbuf)
                    else:
                        break
                elif isinstance(item, bytearray) or \
                     isinstance(item, str):
                    # zzz print('*** sparsefile read', len(item), hexlify(item[:20]))
                    retbuf.extend(item)
                else:
                    raise FuseOSError(EIO)
            return retbuf
        elif offset < self['st_size']:
            # zzz print(offset, self['st_size'])
            size = min(size, self['st_size']-offset)
            xbuf, eof  = file_get_bytes(self.radio, path_list,
                                        size, offset)
            if (xbuf):
                retbuf.extend(xbuf)
                self._add_sparse(offset, xbuf)
            return retbuf
        raise FuseOSError(ENODATA)

    def unlink(self, *args, **kwargs):       # delete
        print('sparse IO unlink', self.sparse)
        self._delete_sparse()
        return 0

    def write(self, path_list, buf, offset):
        print('sparse IO write', offset, len(buf))
        self._open_sparse(path_list)
        sz = self._add_sparse(offset, buf)
        if (offset + sz) > self['st_size']:
            self['st_size'] = offset + sz
        print('sparse IO size',sz)
        return sz


class ImageIOFileHandler(ByteIOFileHandler):
    '''
    Image IO File Handler class

    Performs Image IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(ImageIOFileHandler, self).__init__(radio, ntype, mode, nlinks)

    def flush(self, path_list): # close
        path_list[-1] = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        # zzz print('image io flush', path_list)
        self['st_size'] = im_close_file(self.radio, path_list)
        if (self['st_size']):
            return 0
        raise FuseOSError(ENOENT)

    def getattr(self, path_list, update=False):
        return self

    def read(self, path_list, size, offset):
        # zzz print('image io read, size: {}, offset: {}'.format(size, offset))
        error, buf, offset = im_get_file(self.radio,
                               path_list,
                               size,
                               offset)
        # zzz print(len(buf),eof)
        if (error) and (error is not tlv_errors.SUCCESS):
            raise FuseOSError(ENODATA)
        return str(buf)

    def release(self, path_list): # close
        # zzz
        print('image io release')
        return 0
        raise FuseOSError(ENOENT)

    def unlink(self, path_list):  # delete
        version = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        new_path_list = path_list[:-1]
        new_path_list.append(version)
        # zzz
        print('*** image io unlink', new_path_list)
        if im_delete_file(self.radio, new_path_list):
            return 0
        raise FuseOSError(ENOENT)

    def write(self, path_list, buf, offset):
        # zzz
        print('image io write, size: {}, offset: {}'.format(len(buf), offset))
        error, new_offset = im_put_file(self.radio,
                           path_list,
                           buf,
                           offset)
        print('image io write', error, new_offset)
        if (error) and (error is not tlv_errors.SUCCESS):
            raise FuseOSError(ENOENT)
        if (new_offset):
            return(new_offset - offset)
        else:
            return len(buf)
#        return len(buf) - (new_offset - offset)


class SimpleRecHandler(FileHandler):
    '''Simple Record Handler class

    Performs Simple Record IO.

    A simple record is an object that is referenced by a record
    number rather by a byte offset.  The offset is the record number
    for what ever record we are talking about.

    If we want to write another record to the remote, we have to
    specific the next record number when we do the write.

    We use the file size (st_size) to remember how many records are in the
    object.  So if we want to write another record we have specify
    st_size + 1.

    This also has the nice property of showing up in an 'ls -l note'.  The
    'file size' of note is the last note number written.

    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(SimpleRecHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        if (update):
            attrs = file_update_attrs(self.radio, path_list, self)
            # zzz print('dblk note attrs',attrs)
            if (attrs):
                self = attrs
        return self

    def write(self, path_list, buf, offset):
        last_seq = self['st_size']
        # zzz
        print('SRH:  size: {}, offset: {}, last: {}'.format(
                len(buf), offset, last_seq))
        if (offset and offset != last_seq) or (len(buf) > 200):
            raise FuseOSError(EINVAL)
        self['st_size'] = file_put_bytes(self.radio,
                              path_list, buf, last_seq + 1)
        return len(buf)


class SysFileHandler(FileHandler):
    '''
    System Executive File Handler class

    Performs file specific operations on System Executive Facts.
    This class is dynamically created by SysDirHandler when adding
    image version file names.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(SysFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio


class TestBaseHandler(FileHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestBaseHandler, self).__init__(ntype, mode, nlinks)
        self.buf   = ''
        self['st_size'] = 0
        self.sum   = 0

    def release(self, path_list):      # close
        self.buf   = ''
        self.sum   = 0
        return 0

class TestZerosHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestZerosHandler, self).__init__(ntype, mode, nlinks)

    def read(self, path_list, size, offset):
        buf = chr(0) * size
        return buf

    def write(self, path_list, buf, offset):
        if (buf[0] == 0) and len(Set(buf)) == 1:
            self['st_size'] += len(buf)
            self.sum   += sum(map(ord,buf))
            dsize       = len(buf)
        else:
            raise FuseOSError(EIO)
        return dsize


class TestOnesHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestOnesHandler, self).__init__(ntype, mode, nlinks)

    def read(self, path_list, size, offset):
        buf = chr(0xff) * size
        return (str(buf))

    def write(self, path_list, buf, offset):
        if (buf[0] == 0xff) and len(Set(buf)) == 1:
            self['st_size'] += len(buf)
            self.sum   += sum(map(ord,buf))
            dsize       = len(buf)
        else:
            raise FuseOSError(EIO)
        return dsize


class TestEchoHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, *args, **kwargs):
        super(TestEchoHandler, self).__init__(*args, **kwargs)
        #super(TestEchoHandler, self).__init__(ntype, mode, nlinks)
        self.sparse = None

    def _open_sparse(self, fpath):
        if (self.sparse == None):
            self.sparse = SparseFile('_'.join(fpath))
            items = sorted(self.sparse.items())
            if items:
                offset, block = items[-1]
                self['st_size'] = offset + len(block)
            else:
                self['st_size'] = 0
        print(self.sparse)

    def _close_sparse(self):
        if self.sparse:
            self.sparse.flush()
        print(self.sparse)

    def _delete_sparse(self):
        if self.sparse:
            self.sparse.drop()
            self.sparse = None
            self['st_size'] = 0
        print(self.sparse)

    def flush(self, path_list):
        print('testecho flush', path_list)
        self._close_sparse()
        return 0

    def getattr(self, *args, **kwargs):
        print(args)
        print(kwargs)
        self._open_sparse(args[0])
        super(TestEchoHandler, self).getattr(*args, **kwargs)
        return self

    def read(self, path_list, size, offset):
        print('testecho read', offset, size, path_list)
        if offset >= self['st_size']:
            raise FuseOSError(ENODATA)
        self._open_sparse(path_list)
        retbuf = bytearray()
        size = min(size, self['st_size'] - offset)
        work_list = self.sparse.get_bytes_and_holes(offset, size)
        if (work_list):
            for item in work_list:
                if isinstance(item, tuple) or \
                   isinstance(item, list):
                    print(item)
                    first, last = item
                    last = min(last, self['st_size'])
                    xbuf = bytearray('\x00' * (last - first))
                    if (xbuf):
                        retbuf.extend(xbuf)
                    else:
                        break
                elif isinstance(item, bytearray) or \
                     isinstance(item, str):
                    print('testecho read block', len(item), hexlify(item[:24]))
                    retbuf.extend(item)
                else:
                    print(item)
                    raise FuseOSError(EIO)
            return retbuf
        else:
            retbuf.extend(bytearray('\x00' * size))
            return retbuf
        raise FuseOSError(ENODATA)

    def unlink(self, path_list):       # delete
        print('testecho unlink', self.sparse, path_list)
        self._delete_sparse()
        return 0

    def write(self, path_list, buf, offset):
        print('testecho write', offset, len(buf))
        self._open_sparse(path_list)
        sz = self.sparse.add_bytes(offset, buf)
        if (offset + sz) > self['st_size']:
            self['st_size'] = offset + sz
        print('testecho size',sz)
        return sz


class TestSumHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestSumHandler, self).__init__(ntype, mode, nlinks)

    def getattr(self, path_list, update=False):
        self['st_size'] = self.sum
        return self

    def read(self, path_list, size, offset):
        buf = 'S' * size
        return buf

    def write(self, path_list, buf, offset):
        if (offset == len(self.buf)):
            self['st_size'] += len(buf)
            self.sum   += sum(map(ord,buf))
            dsize       = len(buf)
        else:
            raise FuseOSError(EIO)
        return dsize


class DirHandler(OrderedDict):
    '''
    Base Directory Handler class

    Performs all FUSE directory related operations.
    '''
    def __init__(self, a_dict):
        super(DirHandler, self).__init__(a_dict)
        self.inode = new_inode()

    def traverse(self, path_list, index):
        """
        Traverse the directory tree until reaching the leaf identified
        by path_list.

        returns the handler for which the path_list refers as well
        as the modified path_list.
        The path_list may be modified post execution of the base
        class to handle any required conversion from printable
        filenames to Tagnet TLV types.
        Directory keys are printable filenames.
        """
        # zzz print('dirhandler.traverse', index, path_list)
        if index < (len(path_list) - 1):      # look in subdirectory
            for key, handler in self.iteritems():
                if (path_list[index] == key):
                    # zzz print(isinstance(handler, DirHandler))
                    if isinstance(handler, DirHandler):
                        return handler.traverse(path_list, index + 1)
        else:
            for key, handler in self.iteritems():
                # zzz print('traverse last', key, type(handler))
                # match the terminal name
                if (path_list[index] == key):
                    return (handler, path_list)
        print('*** dirhandler.traverse fail')
        return (None, None)           # no match found

    def create(self, path_list, mode):
        raise FuseOSError(EINVAL)

    def getattr(self, path_list, update=False):
        print('*** getattr', path_list)
        return self['']

    def readdir(self, path_list):
        # zzz print('base class readdir')
        # zzz print(self)
        dir_names = ['.','..']
        for name in self.keys():
            if (name != ''):
                dir_names.append(name)
        # zzz print(dir_names)
        self['']['st_nlink'] = len(dir_names)
        return dir_names

    def link(self, link_name, target):
        print('DirHandler.link', link_name, target)
        return 0

    def unlink(self, path_list):
        print('DirHandler.unlink', path_list)
        return 0

class PollNetDirHandler(DirHandler):
    '''
    Network Polling Directory Handler class

    Performs all FUSE directory related operations.
    '''
    def __init__(self, radio, a_dict):
        super(PollNetDirHandler, self).__init__(a_dict)
        self.radio = radio

    def traverse(self, path_list, index):
        handler, path_list = super(PollNetDirHandler, self).traverse(path_list, index)
        if not path_list:
            return (handler, path_list)
        if (path_list[index] is not '') and \
           (path_list[index][0] is not '.'):
            path_list[index] = '<node_id:' + path_list[index] + '>'
        # zzz print('*** poll net dir', index, path_list)
        return (handler, path_list)

#            name = re.match(r'x[0-9a-fA-F]+', node_id),
#            self['0x'+name] = tagtree()
#                         ImageIOFileHandler(self.radio,
#                                            S_IFREG,
#                                            0o664,
#                                            1)


class ImageDirHandler(DirHandler):
    '''
    Software Images Directory Handler class

    Performs image directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        # zzz print('init imagedirhandler')
        super(ImageDirHandler, self).__init__(a_dict)
        self.radio = radio

    def readdir(self, path_list):
        # zzz print('image readdir', path_list)
        tag_dir = im_get_dir(self.radio, path_list)
        if (tag_dir):
            # make set of versions found on tag
            tag_versions = []
            for version, state in tag_dir:
                print('img readdir version/state',version,str(state))
                if (str(state) != 'x'):
                    tag_versions.append('.'.join(map(str, version)))
            tag_set = Set(tag_versions)
            print('tag_set',tag_set)
            # make set of version founds on self
            my_versions = []
            for version in self.keys():
                if version is not '':
                    my_versions.append(version)
            my_set = Set(my_versions)
            print('my_set',my_set)

            # add versions on tag but not on self
            for version in tag_set.difference(my_set):
                self[version] = ImageIOFileHandler(
                    self.radio,
                    S_IFREG,
                    0o664,
                    1)
            # remove versions on self but not on tag
            for version in my_set.difference(tag_set):
                try:
                    del self[version]
                except KeyError:
                    pass  # wasn't there, ok

        # zzz print(self)
        return super(ImageDirHandler, self).readdir(path_list)

    def create(self, path_list, mode):
        file_name = path_list[-1]
        print('image create',path_list[:-1], oct(mode), file_name)
        try:
            x = self[file_name]
            raise FuseOSError(EEXIST)
        except KeyError:
            self[file_name] = ImageIOFileHandler(self.radio,
                                                 S_IFREG,
                                                 0o664,
                                                 1)
        return 0

    def unlink(self, path_list):  # delete
        print('image dir delete (unlink)', path_list)
        del self[path_list[-1]]   # last element is version
        return 0

    def release(self, path_list): # close
        # zzz
        print('image dir close (release)', path_list)
        return 0


class SysDirHandler(DirHandler):
    '''
    System Active Directory Handler class

    Performs active directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysDirHandler, self).__init__(a_dict)
        self.radio = radio

    def readdir(self, path_list, img_state=''):
        # zzz print('image readdir', path_list)
        tag_dir = im_get_dir(self.radio, path_list)
        if (tag_dir):
            # make set of versions found on tag
            tag_versions = []
            for version, state in tag_dir:
                if (img_state == '') or (img_state == state):
                    tag_versions.append('.'.join(map(str, version)))
            tag_set = Set(tag_versions)
            print('tag_set',tag_set)
            # make set of version founds on self
            my_versions = []
            for version in self.keys():
                if version is not '':
                    my_versions.append(version)
            my_set = Set(my_versions)
            print('my_set',my_set)

            # add versions on tag but not on self
            for version in tag_set.difference(my_set):
                self[version] = ImageIOFileHandler(
                    self.radio,
                    S_IFREG,
                    0o664,
                    1)
            # remove versions on self but not on tag
            for version in my_set.difference(tag_set):
                del self[version]
        # zzz print(self)
        return super(SysDirHandler, self).readdir(path_list)


class SysActiveDirHandler(SysDirHandler):
    '''
    System Active Directory Handler class

    Performs active directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysActiveDirHandler, self).__init__(radio, a_dict)

    def link(self, ln_l, tg_l):
        print('*** SysActive.link', ln_l, tg_l)
        # set new version on tag active directory
        new_version = tg_l[-1]
        ln_lv = ln_l
        ln_lv.append(new_version)
        err = im_set_version(self.radio, ln_lv)
        # if a timeout occurs, we assume success. may need to do better
        if (err == tlv_errors.SUCCESS) or (err == tlv_errors.ETIMEOUT):
            # remove existing link(s), if any
            for version, handler in self.iteritems():
                if version != '':
                    del self[version]
            # add new link
            print('*** sysactive.link', new_version)
            self[new_version] = SysFileHandler(self.radio,
                                        S_IFREG,
                                        0o664,
                                        1)
            return 0
        return 0

    def readdir(self, path_list):
        dir = super(SysActiveDirHandler, self).readdir(path_list, img_state='active')
        print('SysActive.readdir',dir)
        return dir

    def unlink(self, path_list):
        print('SysActive.unlink', path_list)
        return 0


class SysBackupDirHandler(SysDirHandler):
    '''
    System Backup Directory Handler class

    Performs backup directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysBackupDirHandler, self).__init__(radio, a_dict)

    def link(self, ln_l, tg_l):
        print('*** SysBackup.link', ln_l, tg_l)
        # set new version on tag backup directory
        new_version = tg_l[-1]
        ln_lv = ln_l
        ln_lv.append(new_version)
        err = im_set_version(self.radio, ln_lv)
        # if a timeout occurs, we assume success. may need to do better
        if (err == tlv_errors.SUCCESS) or (err == tlv_errors.ETIMEOUT):
            # remove existing link(s), if any
            for version, handler in self.iteritems():
                if version != '':
                    del self[version]
            # add new link
            print('*** sysbackup.link', new_version)
            self[new_version] = SysFileHandler(self.radio,
                                        S_IFREG,
                                        0o664,
                                        1)
            return 0
        return 0

    def readdir(self, path_list):
        dir = super(SysBackupDirHandler, self).readdir(path_list, img_state='backup')
        print('SysBackup.readdir',dir)
        return dir

    def unlink(self, path_list):
        print('SysBackup.unlink', path_list)
        return 0


class SysGoldenDirHandler(SysDirHandler):
    '''
    System Golden Directory Handler class

    Performs Golden directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysGoldenDirHandler, self).__init__(radio, a_dict)


class SysNibDirHandler(SysDirHandler):
    '''
    System NIB Directory Handler class

    Performs NIB directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysNibDirHandler, self).__init__(radio, a_dict)


class SysRunningDirHandler(SysDirHandler):
    '''
    System Running Directory Handler class

    Performs running directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysRunningDirHandler, self).__init__(radio, a_dict)

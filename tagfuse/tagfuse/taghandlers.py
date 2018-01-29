#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
from builtins import *                  # python3 types

import os
import sys

import logging

from   collections   import defaultdict, OrderedDict
from   errno         import ENOENT, ENODATA, EEXIST
from   stat          import S_IFDIR, S_IFLNK, S_IFREG
from   time          import time

__all__ = ['FileHandler',
           'ByteIOFileHandler',
           'ImageIOFileHandler',
           'DblkIONoteHandler',
           'DirHandler',
           'PollNetDirHandler',
           'ImageDirHandler',
           'SysActiveDirHandler',
           'SysActiveDirHandler',
           'SysBackupDirHandler',
           'SysGoldenDirHandler',
           'SysNibDirHandler',
           'SysRunningDirHandler',
]

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [basedir,
                os.path.join(basedir, 'tagfuse'),
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('\n'.join(sys.path))

from radiofile   import file_get_bytes, file_put_bytes, file_update_attrs, dblk_put_note
from radioimage  import im_get_dir, im_put_file, im_get_file, im_delete_file, im_close_file

base_value = 0

def new_inode():
    global base_value
    base_value += 1
    return base_value

def default_file_attrs(ntype, mode, nlinks, size):
        return dict(st_mode=(ntype | mode),
                    st_nlink=nlinks,
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

    def truncate(self, path_list, length):
        return 0

    def unlink(self, path_list):
        return 0

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
        # zzz print(len(buf),eof)
        if (eof):
            raise FuseOSError(ENODATA)
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

class ImageIOFileHandler(ByteIOFileHandler):
    '''
    Image IO File Handler class

    Performs Image IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(ImageIOFileHandler, self).__init__(radio, ntype, mode, nlinks)
        self.radio = radio
        self.open = False

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

    def write(self, path_list, buf, offset):
        # zzz
        print('image io write, size: {}, offset: {}'.format(len(buf), offset))
        error, new_offset = im_put_file(self.radio,
                           path_list,
                           buf,
                           offset)
        if (error) and (error is not tlv_errors.SUCCESS):
            raise FuseOSError(ENOENT)
        return len(buf) - (new_offset - offset)

    def release(self, path_list): # close
        # zzz
        print('image io release')
        if im_close_file(self.radio,
                              path_list):
            return True
        raise FuseOSError(ENOENT)

    def unlink(self, path_list):  # delete
        # zzz
        print('image io unlink')
        path_list[-1] = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        # zzz print(path_list)
        return im_delete_file(self.radio,
                              path_list)

class DblkIONoteHandler(FileHandler):
    '''
    Dblk Note IO File Handler class

    Performs Dblk Note IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(DblkIONoteHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        if (update):
            attrs = file_update_attrs(self.radio, path_list, self)
            print('dblk get attrs',attrs)
            if (attrs):
                self = attrs
        return self

    def write(self, path_list, buf, offset):
        # zzz print('dblk io note, size: {}, offset: {}'.format(len(buf), offset))
        if (offset) or (len(buf) > 200):
            raise FuseOSError(ENODATA)
        return dblk_put_note(self.radio,
                             path_list,
                             buf)

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
        """
        # zzz
        print(index, path_list)
        if index < (len(path_list) - 1):      # look in subdirectory
            for key, handler in self.iteritems():
                # zzz
                print('traverse',
                      path_list[index],
                      path_list[index] == key,
                      key,
                      type(handler),
                      isinstance(handler, DirHandler),
                      type(DirHandler))
                if (path_list[index] == key):
                    print(isinstance(handler, DirHandler))
                    if isinstance(handler, DirHandler):
                        return handler.traverse(path_list, index + 1)
            return None           # no match found
        else:
            for key, handler in self.iteritems():
                # zzz
                print('traverse last',
                      path_list[index],
                      path_list[index] == key,
                      key,
                      type(handler))
                if (path_list[index] == key):
                    return handler   # match the terminal name
            return None

    def getattr(self, path_list, update=False):
        print('getattr', path_list)
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

class PollNetDirHandler(DirHandler):
    '''
    Network Polling Directory Handler class

    Performs all FUSE directory related operations.
    '''
    def __init__(self, radio, a_dict):
        super(PollNetDirHandler, self).__init__(a_dict)
        self.radio = radio

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
        dir_list = im_get_dir(self.radio, path_list)
        # zzz
        print('image dir list:', dir_list)
        if (dir_list):
            for version, state in dir_list:
                # zzz print(version, state)
                if state.lower() in 'active backup valid':
                    file_name = '.'.join(map(str, version))
                    # zzz print(file_name)
                    try:
                        x = self[file_name]
                        # already exists, don't create again
                    except:
                        self[file_name] = ImageIOFileHandler(
                                                    self.radio,
                                                    S_IFREG,
                                                    0o664,
                                                    1)
        # zzz print(self)
        return super(ImageDirHandler, self).readdir(dir_list)

    def create(self, path_list, mode, file_name):
        print('image create',path_list,mode, file_name)
        try:
            x = self[file_name]
            raise FuseOSError(EEXIST)
        except KeyError:
            self[file_name] = ImageIOFileHandler(self.radio,
                                                 S_IFREG,
                                                 0o664,
                                                 1)
        return True

    def unlink(self, path_list):
        base, name = os.path.split(path)
        print('image dir unlink', path_list, name)
        try:
            del self[name]
            return True
        except KeyError:
            return False

    def release(self, path_list): # close
        # zzz
        print('image dir release', path_list)
#        try:
#            del self[path_list[-1]]
#        except:
#            raise FuseOSError(ENOENT)
#        return 0

class SysActiveDirHandler(DirHandler):
    '''
    System Active Directory Handler class

    Performs active directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysActiveDirHandler, self).__init__(a_dict)
        self.radio = radio

class SysBackupDirHandler(DirHandler):
    '''
    System Backup Directory Handler class

    Performs backup directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysBackupDirHandler, self).__init__(a_dict)
        self.radio = radio

class SysGoldenDirHandler(DirHandler):
    '''
    System Golden Directory Handler class

    Performs Golden directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysGoldenDirHandler, self).__init__(a_dict)
        self.radio = radio

class SysNibDirHandler(DirHandler):
    '''
    System NIB Directory Handler class

    Performs NIB directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysNibDirHandler, self).__init__(a_dict)
        self.radio = radio

class SysRunningDirHandler(DirHandler):
    '''
    System Running Directory Handler class

    Performs running directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysRunningDirHandler, self).__init__(a_dict)
        self.radio = radio

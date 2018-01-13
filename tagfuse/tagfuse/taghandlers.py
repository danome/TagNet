#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

from   collections   import defaultdict, OrderedDict
from   errno         import ENOENT, ENODATA
from   stat          import S_IFDIR, S_IFLNK, S_IFREG
from   sys           import argv, exit
from   time          import time

from Si446xFile      import file_get_bytes, file_put_bytes, file_update_attrs, dblk_put_note

class FileHandler(OrderedDict):
      '''
      Base File Handler class

      Performs all FUSE file related operations.
      '''
      def __init__(self, ntype, mode, nlinks):
            a_dict = dict(st_mode=(ntype | mode),
                      st_nlink=nlinks,
                      st_size=1,
                      st_ctime=time(),
                      st_mtime=time(),
                      st_atime=time())
            super(FileHandler, self).__init__(a_dict)

      def __len__(self):
            return 1

      def getattr(self, path_list, update=False):
            return self

      def truncate(self, path_list, length):
            return 0

class ByteIOFileHandler(FileHandler):
      def __init__(self, radio, ntype, mode, nlinks):
            super(ByteIOFileHandler, self).__init__(ntype, mode, nlinks)
            self.radio = radio

      def getattr(self, path_list, update=False):
            if (update):
                  self = file_update_attrs(self.radio, path_list, self)
            return self

      def read(self, path_list, size, offset):
            # zzz print('byte io read, size: {}, offset: {}'.format(size, offset))
            buf, eof = file_get_bytes(self.radio,
                                      path_list[-3],
                                      path_list[-1],
                                      size,
                                      offset)
            # zzz print(len(buf),eof)
            eof = False
            if (eof):
                  raise FuseOSError(ENODATA)
            return str(buf)

      def write(self, path_list, buf, offset):
            # zzz print('byte io write, size: {}, offset: {}'.format(len(buf), offset))
            return file_put_bytes(self.radio,
                                  path_list[-3],
                                  path_list[-1],
                                  buf,
                                  offset)

class DblkIONoteHandler(FileHandler):
      def __init__(self, radio, ntype, mode, nlinks):
            super(DblkIONoteHandler, self).__init__(ntype, mode, nlinks)
            self.radio = radio

      def getattr(self, path_list, update=False):
            if (update):
                  self = file_update_attrs(self.radio, path_list, self)
            return self

      def write(self, path_list, buf, offset):
            # zzz print('dblk io note, size: {}, offset: {}'.format(len(buf), offset))
            if (offset) or (len(buf) > 200):
                  raise FuseOSError(ENODATA)
            return dblk_put_note(self.radio,
                                 buf)

class DirHandler(OrderedDict):
      '''
      Base Directory Handler class

      Performs all FUSE directory related operations.
      '''
      def __init__(self, a_dict):
            super(self.__class__, self).__init__(a_dict)
#            self.attrs = self[''].attrs

      def traverse(self, path_list, index):
            """
            Traverse the directory tree until reaching the leaf identified
            by path_list.
            """
#            print(path_list)
            if index < (len(path_list) - 1):        # look in subdirectory
                  for key, handler in self.iteritems():
#                        print(key, handler)
                        if (path_list[index] == key):
                              if isinstance(handler, DirHandler):
                                    return handler.traverse(path_list, index + 1)
                  return None               # no match found
            else:
                  for key, handler in self.iteritems():
#                        print(key, handler)
                        if (path_list[index] == key):
                              return handler   # match the terminal name
                  return None

      def getattr(self, path_list, update=False):
            return self['']

      def readdir(self, path_list):
            dir_names = []
            for key  in self.keys():
                  if (key != ''):
                        dir_names.append(key)
            return dir_names

      def test(self, param):
            print(param)

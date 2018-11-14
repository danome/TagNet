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
           'RtcFileHandler',
           'SparseIOFileHandler',
           'ImageIOFileHandler',
           'SimpleIORecHandler',
           'DirHandler',
           'RootDirHandler',
           'PollNetDirHandler',
           'ImageDirHandler',
           'RssiFileHandler',
           'SysActiveDirHandler',
           'SysBackupDirHandler',
           'SysGoldenDirHandler',
           'SysNibDirHandler',
           'SysRunningDirHandler',
           'TxPowerFileHandler',
           'VerbosityDirHandler',
]

import os
import sys
import inspect
import logging
import structlog

###############################

from   sets          import Set
from   collections   import defaultdict, OrderedDict
from   errno         import ENOENT, ENODATA, EEXIST, EPERM, EINVAL, EIO
from   stat          import S_IFDIR, S_IFLNK, S_IFREG
from   time          import time
from   sets          import Set
from   fuse          import FuseOSError
from   binascii      import hexlify
from   datetime      import datetime

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

try:
    from radiofile   import file_get_bytes, file_put_bytes, file_update_attrs, simple_get_record, file_truncate
    from radioimage  import im_put_file, im_get_file, im_delete_file, im_close_file
    from radioimage  import im_get_dir, im_set_version
    from radioutils  import path2list, radio_poll, radio_get_rtctime, radio_set_rtctime, radio_set_power, radio_get_power
    from tagfuseargs import get_cmd_args, set_verbosity, taglog, rootlog
    from sparsefile  import SparseFile
except ImportError:
    from tagfuse.radiofile   import file_get_bytes, file_put_bytes, file_update_attrs, simple_get_record
    from tagfuse.radioimage  import im_put_file, im_get_file, im_delete_file, im_close_file
    from tagfuse.radioimage  import im_get_dir, im_set_version
    from tagfuse.radioutils  import path2list, radio_poll, radio_get_rtctime, radio_set_rtctime, radio_set_power, radio_get_power
    from tagfuse.tagfuseargs import get_cmd_args, set_verbosity, taglog, rootlog
    from tagfuse.sparsefile  import SparseFile

from tagnet              import tlv_errors, TagTlv


# new_inode            return next monotonically increasing number
#
base_value = 0
def new_inode():
    global base_value
    base_value += 1
    return base_value

# default_file_attrs   return default file attributes dict
#
def default_file_attrs(ntype, mode, nlinks, size):
        return dict(st_mode=(ntype | mode),
                    st_nlink=nlinks,
                    st_uid=os.getuid(),
                    st_gid=os.getgid(),
                    st_blksize=512,
                    st_size=size,
                    st_ctime=time(),
                    st_mtime=-1,
                    st_atime=-1,
                    rssi=0)


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
        self.log = structlog.getLogger('fuse.log-mixin.tagfuse.' + __name__).bind(
                scope=self.__class__.__name__)
        if get_cmd_args().verbosity > 4:
            self.log.debug('initialized',
                           method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           ntype=ntype,
                           mode=mode,
                           nlinks=nlinks,
                           inode=self.inode,
                           name=self.__class__.__name__)

    def __len__(self):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           size=1)
        return 1

    def getattr(self, path_list, update=False):
        self['st_atime'] = time()  # set access time
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           atime=self['st_atime'],
                           update=update,
                           path_list=path_list,)
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           attrs=self.__repr__(),
                           path_list=path_list,)
        return self

    def flush(self, path_list):
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list)
        return 0

    def link(self, link_name, target): # hard link
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list)
        raise FuseOSError(EPERM)

    def read(self, path_list, size, offset):
        raise FuseOSError(ENODATA)

    def release(self, path_list):      # close
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list)
        return 0

    def truncate(self, path_list, length):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list)
        return 0

    def unlink(self, path_list):       # delete
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list)
        return 0
        # parent directory does the deleting

    def utimens(self, path_list, times):
        atime, mtime = times
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           times={'access':atime, 'modified':mtime},
                           path_list=path_list, )
        return 0

    def write(self, path_list, buf, offset):
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list, offset=offset)
        raise FuseOSError(EPERM)


class ByteIOFileHandler(FileHandler):
    '''
    Byte IO File Handler class

    Performs Byte IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(ByteIOFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        if (update):
            file_update_attrs(self.radio, path_list, self)
        return super(ByteIOFileHandler, self).getattr(path_list, update=update)


    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           size=size,
                           offset=offset,
                           path_list=path_list, )
        buf, eof = file_get_bytes(self.radio,
                                  path_list,
                                  size,
                                  offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           size=len(buf),
                           eof=eof,
                           path_list=path_list, )
        return buf

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           size=size,
                           offset=offset,
                           path_list=path_list, )
        return file_put_bytes(self.radio,
                        path_list,
                        buf,
                        offset)

    def truncate(self, path_list, length):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list)
        return file_truncate(self.radio,
                             path_list,
                             length)


class XyzFileHandler(FileHandler):
    '''
    Tagnet GPS/XYZ Tlv Type Handler class

    Performs operations on Tag's GPS XYZ position sensor.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(XyzFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        return super(XyzFileHandler, self).getattr(path_list, update=update)

    def read(self, path_list, size, offset):
        if offset == 0:
            return ''
        xyz, geo = radio_get_position(self.radio,
                                 node=TagTlv(str(path_list[0])))
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           xyz=xyz,
                           geo=geo, )
        return xyz.__repr__()

class RtcFileHandler(FileHandler):
    '''
    Tagnet RTC Tlv Type Handler class

    Performs operations on Tag's real time clock. Can get current value
    as well as set it using either utimens (touch) or echo '0' > rtc
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(RtcFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        if update:
            epoch = datetime.utcfromtimestamp(0)
            utctime, a, b, c = radio_get_rtctime(self.radio,
                                    node=TagTlv(str(path_list[0])))
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                               utctime=utctime, )
            try:
                self['st_mtime'] = (utctime - epoch).total_seconds()
            except TypeError:
                self['st_mtime'] = -2
            if get_cmd_args().verbosity > 1:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                               utctime=utctime,
                               modified=self['st_mtime'], )
        return super(RtcFileHandler, self).getattr(path_list, update=update)

    def write(self, path_list, buf, offset):
        if offset:
            raise AttributeError
        radio_set_rtctime(self.radio,
                          datetime.utcnow(),
                          node=TagTlv(str(path_list[0])))
        return len(buf)

    def utimens(self, path_list, times):
        '''
        set tag rtctime to mtime (modified time) and
        update the local atime and mtime attributes.
        '''
        atime, mtime = times
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           times={'access':atime, 'modified':mtime}, )
        utctime = datetime.utcfromtimestamp(mtime)
        radio_set_rtctime(self.radio,
                          utctime,
                          node=TagTlv(str(path_list[0])))
        self['st_atime'] = atime
        self['st_mtime'] = mtime
        self.log.info(method=inspect.stack()[0][3],
                           utctime=utctime, )


class SparseIOFileHandler(ByteIOFileHandler):
    '''
    '''
    def __init__(self, *args, **kwargs):
        super(SparseIOFileHandler, self).__init__(*args, **kwargs)
        self.sparse = None
        self.path = None

    def _open_sparse(self, fpath):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           sparse=self.sparse, disable=get_cmd_args().disable_sparse,
                           sparse_dir=get_cmd_args().sparse_dir, )
        if self.sparse is not None or get_cmd_args().disable_sparse:
            if get_cmd_args().verbosity > 2:
                self.log.debug('early exit', method=inspect.stack()[0][3],
                                          lineno=sys._getframe().f_lineno,)
            return
        sparse_filename = os.path.join(
            get_cmd_args().sparse_dir,
            '_'.join(fpath))
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           file=sparse_filename,
                           sparse=self.sparse, )
        self.path = sparse_filename
        try:
            self.sparse = SparseFile(sparse_filename, get_cmd_args)
            self.log.info(method=inspect.stack()[0][3],
                           path=sparse_filename, )
        except:
            self.log.info('failed', method=inspect.stack()[0][3],
                          path=sparse_filename)
            raise
        items = sorted(self.sparse.items())
        if items:
            offset, block = items[-1]
            if self['st_size'] < (offset + len(block)):
                self['st_size'] = offset + len(block)
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           count=len(items), sparse=self.sparse)

    def _get_sparse(self, offset, size):
        if self.sparse is None or get_cmd_args().disable_sparse_read:
            return []
        return self.sparse.get_bytes_and_holes(offset, size)

    def _add_sparse(self, offset, buf):
        if self.sparse is not None:
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                               offset=offset, size=len(buf))
            return self.sparse.add_bytes(offset, buf)
        return len(buf) # acknowledge but ignore data

    def _close_sparse(self):
        if self.sparse is not None:
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                          lineno=sys._getframe().f_lineno,
                               path=self.path)
            self.sparse.flush()

    def _delete_sparse(self):
        if self.sparse is not None:
            self.sparse.clear()
            self.sparse.flush()
            self.sparse.drop()
            self.sparse = None
            self['st_size'] = 0
            self.log.info('deleted', method=inspect.stack()[0][3],
                          path=self.path)

    def flush(self, *args, **kwargs):
        self.log.info(method=inspect.stack()[0][3],
                      args=args[0],
                      path=self.path)
        self._close_sparse()
        super(SparseIOFileHandler, self).flush(*args, **kwargs)
        return 0

    def getattr(self, path_list, update=False):
        self.path = path_list
        self._open_sparse(path_list)
        return super(SparseIOFileHandler, self).getattr(path_list, update=update)

    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           offset=offset,
                           size=size,
                           old_size=self['st_size'])
        # refresh the file size if seeking beyond our current size
        if offset >= self['st_size']:
            super(SparseIOFileHandler, self).getattr(path_list, update=True)
        if offset >= self['st_size']:
            self.log.info('out of data',
                          method=inspect.stack()[0][3],
                          lineno=sys._getframe().f_lineno,
                          size=size,
                          offset=offset,)
            raise FuseOSError(ENODATA)
        try:
            self._open_sparse(path_list)
        except:
            self.log.warn('sparse file open failure',
                          method=inspect.stack()[0][3],
                          lineno=sys._getframe().f_lineno,
                          path_list=path_list,)
            raise
        retbuf = bytearray()
        size = min(size, self['st_size'] - offset)
        work_list = self._get_sparse(offset, size)
        if (work_list):
            for item in work_list:
                if get_cmd_args().verbosity > 2:
                    self.log.debug(method=inspect.stack()[0][3],
                                   lineno=sys._getframe().f_lineno,
                                   size=len(item),
                                   data=type(item))
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
                    retbuf.extend(item)
                else:
                    raise FuseOSError(EIO)
        elif offset < self['st_size']:
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                               offset=offset,
                               size=self['st_size'])
            size = min(size, self['st_size']-offset)
            xbuf, eof  = file_get_bytes(self.radio, path_list,
                                        size, offset)
            if (xbuf):
                retbuf.extend(xbuf)
                self._add_sparse(offset, xbuf)
        if retbuf:
            if get_cmd_args().verbosity > 1:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                               size=len(retbuf),
                               sample=hexlify(retbuf[:20]))
            return retbuf
        raise FuseOSError(ENODATA)

    def unlink(self, *args, **kwargs):       # delete
        self.log.info(method=inspect.stack()[0][3],
                      path=self.path,
                      sparse=self.sparse)
        self._delete_sparse()
        return 0

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           offset=offset,
                           size=len(buf), )
        self._open_sparse(path_list)
        sz = self._add_sparse(offset, buf)
        if (offset + sz) > self['st_size']:
            self['st_size'] = offset + sz
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           offset=offset, size=sz, )
        return sz


class ImageIOFileHandler(ByteIOFileHandler):
    '''
    Image IO File Handler class

    Performs Image IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(ImageIOFileHandler, self).__init__(radio, ntype, mode, nlinks)
        self.offset = 0

    def getattr(self, path_list, update=False):
        path_list[-1] = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        return super(ImageIOFileHandler, self).getattr(path_list, update=update)

    def flush(self, path_list): # close
        path_list[-1] = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        self['st_size'] = im_close_file(self.radio, path_list, self.offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list,
                           size=self['st_size'])
        return 0

    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=size,)
        error, buf, offset = im_get_file(self.radio,
                               path_list,
                               size,
                               offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           eof=eof,
                           size=len(buf),
                           error=error)
        if (error) and (error is not tlv_errors.SUCCESS):
            raise FuseOSError(ENODATA)
        return str(buf)

    def release(self, path_list): # close
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        return 0

    def unlink(self, path_list):  # delete
        version = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        new_path_list = path_list[:-1]
        new_path_list.append(version)
        self.log.info(method=inspect.stack()[0][3],
                      version=version, path_list=path_list)
        if im_delete_file(self.radio, new_path_list):
            return 0
        raise FuseOSError(ENOENT)

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=len(buf), )
        error, new_offset = im_put_file(self.radio,
                           path_list,
                           buf,
                           offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=new_offset, size=len(buf))
        if (error) and (error is not tlv_errors.SUCCESS):
            raise FuseOSError(ENOENT)
        if (new_offset):
            self.offset = new_offset
            return(new_offset - offset)
        else:
            return len(buf)


class SimpleIORecHandler(FileHandler):
    '''
    Simple Record Handler class

    Performs Simple Record IO. A simple record is an object that
    references a singleton data structure on the Tag, such as
    the current GPS position.

    When writing another record to the remote tag, use the file
    size (st_size in file attribytes) to remember a sequence
    number to allow the tag to detect duplicate requests. So if
    we to write another record we have specify a offset using
    st_size + 1.

    This also has the nice property of showing up in 'ls -l note'.
    The 'file size' of note is the sequence number of the last note
    written.

    When reading a record, the requested offset must be zero. The
    returned data is decoded into a JSON structure based on the
    content of the response.
    - TagNet TLVs are self-defined and can be decoded with no
      additional information
    - Data blocks are decoded based on the structure type
      identifier, either a TagCore type or a TagNet Adapter type
      (see those components for specific structure  definitions
      that are avaialble to decode).
    The decoded JSON string is the data returned to the Fuse
    read call.

    In addition to the tag data, the JSON also contains the
    timestamp associated with the record, the RSSI strength
    reading of the received message, and the st_size value.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(SimpleIORecHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio
        self.eof = False

    def getattr(self, path_list, update=False):
        if (update):
            file_update_attrs(self.radio, path_list, self)
        return super(SimpleIORecHandler, self).getattr(path_list, update=update)

    def write(self, path_list, buf, offset):
        last_seq = self['st_size']
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list,
                           size=len(buf),
                           offset=offset,
                           sequence=last_seq)
        if (offset) or (len(buf) > 200):
            self.log.warn(method=inspect.stack()[0][3],
                          lineno=sys._getframe().f_lineno,
                          size=self['st_size'],
                          sample=hexlify(buf[:20]),
                          path_list=path_list)
            raise FuseOSError(EINVAL)
        self['st_size'] = file_put_bytes(self.radio,
                              path_list, buf, last_seq + 1)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           size=self['st_size'],
                           sample=hexlify(buf[:20]),
                           path_list=path_list)
        return len(buf)

    def _json_output(self, tlv_list):
        return tlv_list.json_repr() if tlv_list else ''

    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list,
                           size=size,
                           offset=offset,
                           eof=self.eof)

        # gotta read from the beggining, this is simple rec read
        if offset > 0:
            self.log.warn('offset not zero',
                          method=inspect.stack()[0][3],
                          offset=offset, path_list=path_list)
            return ''
            raise FuseOSError(ENODATA)

        # get the record from the tag
        err, payload, meta = simple_get_record(self.radio, path_list)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           error=err,
                           this=[type(tlv) for tlv in payload])
        if get_cmd_args().verbosity > 4:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           rssi=meta[0],
                           send_status=meta[1],
                           recv_status=meta[2],)
        # return JSON output text
        if (err is tlv_errors.SUCCESS or err is tlv_errors.EODATA):
            if err is tlv_errors.EODATA: self.eof = True
            return self._json_output(payload) + '\n'
        self.log.warn(method=inspect.stack()[0][3],
                      lineno=sys._getframe().f_lineno,
                      error=err,
                      eof=self.eof,
                      path_list=path_list)
        return ''

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


class RssiFileHandler(FileHandler):
    '''
    RSSI Measurement File Handler class

    performs reading and reporting Radio signal strength indicator.
    '''
    def __init__(self, radio, rssi_stash, ntype, mode, nlinks):
        '''
        The local variable indicates the name of the tree-node
        that provides the receive RSSI value as its st_size.
        '''
        super(RssiFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio
        self.rssi_stash = rssi_stash

    def getattr(self, path_list, update=False):
        '''
        The receive RSSI is sampled during receipt of the most
        recent response to the Tag's get attributes request
        and stored on the object referred by rssi_stash. If
        no referral, then this is the stash object so just
        return current attributes.
        '''
        if self.rssi_stash:
            if update:
                file_update_attrs(self.radio, path_list, self)
                self.parent[self.rssi_stash]['st_size'] = self['rssi']
                self.parent[self.rssi_stash]['st_mtime'] = self['st_mtime']
        return super(RssiFileHandler, self).getattr(path_list, update=update)

class TxPowerFileHandler(FileHandler):
    '''
    Transmit Power File Handler class

    Performs reading and reporting Radio transmitter power level.
    Handles both local and remote power control by using the rssi_stash
    variable to denote whether controlling power of the remote tag or
    else the local radio. If remote, then send request to tag and
    use the response data to set the st_size as well as set the
    rssi_stash.
    '''
    def __init__(self, radio, rssi_stash, ntype, mode, nlinks):
        super(TxPowerFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio
        self.rssi_stash = rssi_stash

    def getattr(self, path_list, update=False):
        if self.rssi_stash:
            if update:
                power, rssi, _, _ = radio_get_power(self.radio,
                                                    node=TagTlv(str(path_list[0])))
                self['rssi'] = rssi
                if power:
                    self['st_size'] = power
                    self['st_mtime'] = time()
                else:
                    self['st_size'] = 0
                    self['st_mtime'] = -2
                self.parent[self.rssi_stash]['st_size'] = self['rssi']
                self.parent[self.rssi_stash]['st_mtime'] = self['st_mtime']
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                               path_list=path_list,
                               time=self['st_mtime'], size=self['st_size'],
                               rssi=self['rssi'])
        else:
            if update:
                self['st_size'] = self.radio.get_power()
                self['st_mtime'] = time()

        return super(TxPowerFileHandler, self).getattr(path_list, update=update)

    def truncate(self, path_list, power):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list,
                           power=power)
        if self.rssi_stash:
            radio_set_power(self.radio, power, node=TagTlv(str(path_list[0])))
        else:
            self.radio.set_power(power)
        return 0


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
        self.sparse = None

    def _open_sparse(self, fpath):
        if (self.sparse == None):
            self.sparse = SparseFile('_'.join(fpath), get_cmd_args)
            items = sorted(self.sparse.items())
            if items:
                if get_cmd_args().verbosity > 2:
                    self.log.debug(method=inspect.stack()[0][3],get_file_size(tempfile) lineno=sys._getframe().f_lineno,
                                   size=len(items))
                offset, block = items[-1]
                self['st_size'] = offset + len(block)
            else:
                self['st_size'] = 0
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           sparse=self.sparse)

    def _close_sparse(self):
        if self.sparse:
            self.sparse.flush()
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           sparse=self.sparse)

    def _delete_sparse(self):
        if self.sparse:
            self.sparse.drop()
            self.sparse = None
            self['st_size'] = 0
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           sparse=self.sparse)

    def flush(self, path_list):
        self.log.debug(method=inspect.stack()[0][3],
                       lineno=sys._getframe().f_lineno,
                       path_list=path_list, )
        self._close_sparse()
        return 0

    def getattr(self, path_list, update=False):
        self._open_sparse(path_list)
        return super(TestEchoHandler, self).getattr(path_list, update=update)

    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           offset=offset,
                           size=size,
                           path_list=path_list, )
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
                    if get_cmd_args().verbosity > 2:
                        self.log.debug(method=inspect.stack()[0][3],
                                       lineno=sys._getframe().f_lineno,
                                       data=item)
                    first, last = item
                    last = min(last, self['st_size'])
                    xbuf = bytearray('\x00' * (last - first))
                    if (xbuf):
                        retbuf.extend(xbuf)
                    else:
                        break
                elif isinstance(item, bytearray) or \
                     isinstance(item, str):
                    if get_cmd_args().verbosity > 2:
                        self.log.debug(method=inspect.stack()[0][3],
                                       lineno=sys._getframe().f_lineno,
                                       size=len(item), data=hexlify(item[:24]))
                    retbuf.extend(item)
                else:
                    if get_cmd_args().verbosity > 2:
                        self.log.debug(method=inspect.stack()[0][3],
                                       lineno=sys._getframe().f_lineno,
                                       error=EIO, data=item)
                    raise FuseOSError(EIO)
            return retbuf
        else:
            retbuf.extend(bytearray('\x00' * size))
            return retbuf
        raise FuseOSError(ENODATA)

    def unlink(self, path_list):       # delete
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           sparse=self.sparse,
                           path_list=path_list)
        self._delete_sparse()
        return 0

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           offset=offset,
                           size=len(buf),)
        self._open_sparse(path_list)
        sz = self.sparse.add_bytes(offset, buf)
        if (offset + sz) > self['st_size']:
            self['st_size'] = offset + sz
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           size=sz,)
        return sz


class TestSumHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestSumHandler, self).__init__(ntype, mode, nlinks)

    def getattr(self, path_list, update=False):
        self['st_size'] = self.sum
        return super(TestSumHandler, self).getattr(path_list, update=update)

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
        self.log = structlog.getLogger('fuse.log-mixin.tagfuse.' + __name__).bind(
                scope=self.__class__.__name__)
        if get_cmd_args().verbosity > 4:
            self.log.debug('initialized',
                           method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           name=self.__class__.__name__)
        self.root = None
        self.parent = None

    def traverse(self, root, parent, path_list, index):
        """
        Traverse the directory tree until reaching the leaf identified
        by path_list.

        returns the handler for which the path_list refers as well
        as the modified path_list.
        The path_list may be modified post execution of the base
        class to handle any required conversion from printable
        filenames to Tagnet TLV types.
        Directory keys are printable filenames.
        The parent and root values for each node traversed is set
        based on input. This is a kludgy way to make sure all of
        the nodes have been properly initialized. This can't be
        done at object.__init__() because the initialization of
        the Root Tree happens before the root node id is known.
        Since nodes in the tree can be dynamically added or
        removed at any time we would have to make sure that it
        is properly initialized. Doing it here makes sure that
        every node is set, albeit a little extra overhead
        since it mught have already been set by previous call.
        """
        self.root = root
        self.parent = parent
        if get_cmd_args().verbosity > 4:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           root=type(root), parent=type(parent),
                           index=index, path_list=path_list)
        if index < (len(path_list) - 1):      # look in subdirectory
            for key, handler in self.iteritems():
                handler.root = root
                handler.parent = self
                if (path_list[index] == key):
                    if isinstance(handler, DirHandler):
                        return handler.traverse(root, self, path_list, index + 1)
        else:
            for key, handler in self.iteritems():
                handler.root = root
                handler.parent = self
                if get_cmd_args().verbosity > 4:
                    self.log.debug(method=inspect.stack()[0][3],
                                   lineno=sys._getframe().f_lineno,
                                   name=key, handler=type(handler))
                # match the terminal name
                if (path_list[index] == key):
                    return (handler, path_list)
            self.log.warn('fail', method=inspect.stack()[0][3],
                      index=index, path_list=path_list)
        return (None, None)           # no match found

    def create(self, path_list, mode):
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list)
        raise FuseOSError(EINVAL)

    def getattr(self, path_list, update=False):
        print('*** dir.getattr', get_cmd_args().verbosity)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list, update=update)
        return self['']

    def readdir(self, path_list):
        dir_names = ['.','..']
        for name in self.keys():
            if (name != ''):
                dir_names.append(name)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           dir_list=dir_names,
                           path_list=path_list)
        self['']['st_nlink'] = len(dir_names)
        return dir_names

    def link(self, link_name, target):
        self.log.info(method=inspect.stack()[0][3],
                      link_name=link_name,
                      target=target)
        return 0

    def unlink(self, path_list):
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list)
        return 0

    def utimens(self, path_list, times):
        atime, mtime = times
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           times={'access':atime, 'modified':mtime},
                           path_list=path_list, )
        return 0


class RootDirHandler(DirHandler):
    '''
    Tag Tree Root Directory Handler class
    '''
    def __init__(self, tag_fn, a_dict):
        '''
        tag_fn provides the function to call when creating new
        tag instances in the Tag Tree.
        '''
        super(RootDirHandler, self).__init__(a_dict)
        self.tag_fn = tag_fn
        self.root = None
        self.parent = None

    def traverse(self, root, parent, path_list, index):
        '''
        perform normal traverse operation followed by a fixup of
        the node_id string in the path_list. Want to convert
        from human readable to <k:v> format so that proper type
        is associated with this path element. When converting
        the path element, don't modify if element is the empty
        string (file attributes) or a dot file (special in this
        level).
        '''
        self.root = root
        self.parent = parent
        handler, path_list = super(RootDirHandler, self).traverse(root, self, path_list, index)
        if path_list and path_list[index] is not '' and not path_list[index].startswith('.'):
            path_list[index] = '<node_id:' + path_list[index] + '>'
        if get_cmd_args().verbosity > 4:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           root=type(root), parent=type(parent),
                           index=index, path_list=path_list)
        return (handler, path_list)


# number of times to keep polling after first new tag has been found
# this gives a chance for missed communication
MAX_POLL = 1

class PollNetDirHandler(DirHandler):
    '''
    Network Polling Directory Handler class

    Performs polling for new tags and adds them to root directory.
    '''
    def __init__(self, radio, known, a_dict):
        '''
        radio      instance of radio to use for I/O
        count      maximum number of iterations to poll
        known    name of directory with tags found by
                   previous poll
        '''
        super(PollNetDirHandler, self).__init__(a_dict)
        self.radio    = radio
        self.known    = known

    def create(self, path_list, mode):
        file_name = path_list[-1]
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list[:-1],
                      mode=oct(mode),
                      file=file_name)
        # add if this instance is poll/known handler
        if self.parent[self.known] == self:
            try:
                x = self.parent[self.known][file_name]
                raise FuseOSError(EEXIST)
            except KeyError:
                self.parent[self.known][file_name] = FileHandler(S_IFREG, 0o444, 1)
                self.parent[self.known][file_name]['st_mtime'] = time()
        return 0

    def unlink(self, path_list):       # delete
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list)
        try:
            del self[path_list[-1]]
            self['']['st_nlink'] -= 1
        except:
            if get_cmd_args().verbosity > 1:
                self.log.debug('file not found', method=inspect.stack()[0][3],lineno=sys._getframe().f_lineno,
                               path_list=path_list, )
        return 0

    def utimens(self, path_list, times):
        '''
        look for any new tags in the neighborhood and add them
        to this node's children. A whole new instance of the
        tagtree is instantiated for each tag. Existing tags that
        are no longer reachable stay in the tree and must be
        explicitly deleted.
        radio_poll returns a 4-tuple of which we only are
        interested in the first item (not interested in rssi,
        tx status, rx status).
        The tag_list is a list of all tags that responded to the
        poll. Each item in the list is a tuple of info about that
        tag. The first item is its node id, which we use for the
        directory entry name.
        '''
        atime, mtime = times
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           times={'access':atime, 'modified':mtime},
                           path_list=path_list, )

        # don't wait more than 10 minutes
        if (time() - mtime) > ((10 * 60) + 1):
            raise FuseOSError(EINVAL)

        if get_cmd_args().verbosity > 2:
            self.log.info(method=inspect.stack()[0][3],
                          parent=type(self.parent),
                          known=type(self.parent[self.known]),
                          me=type(self), )

        # clean directory of tags previously if new search
        if self.parent[self.known] is not self:
            for tag in self.keys():
                if tag is '' or tag.startswith('.'):
                    continue
                del self[tag]

        # build list of existing tag names from poll/known
        known_names = []
        for tag in self.parent[self.known].keys():
            if tag is '' or tag.startswith('.'):
                continue          # skip special files
            known_names.append(tag)
        known_set = Set(known_names) # tags currently known

        # poll for list of new tags
        tag_set = Set()           # tags found by polling
        new_set = Set()           # tags added to new list
        more = 0
        while time() < mtime:
            tag_set |= Set(radio_poll(self.radio).keys())
            new_set |= tag_set.difference(known_set)
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                              local=known_set,
                              new=new_set,
                              tag=tag_set)
            if new_set:             # stop if any found
                if more > MAX_POLL: # keep looking for a few more
                    break
                more += 1
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           known=known_set,
                           new=new_set,
                           all=tag_set)

        # add newly discovered tags
        for tag in new_set:
            # Add new Tag tree onto root of TagFuse tree
            # and use passed function to instantiate it
            self.root[tag] = self.root.tag_fn(self.radio)
            self.root['']['st_nlink'] += 1

            # add tag to poll/new directory
            self[tag] = FileHandler(S_IFREG, 0o444, 1)
            self[tag]['st_mtime'] = time()
            self['']['st_nlink'] += 1

            # add tag to poll/known directory, if not this object
            if self.parent[self.known] is not self:
                self.parent[self.known][tag] = FileHandler(S_IFREG, 0o444, 1)
                self.parent[self.known][tag]['st_mtime'] = time()
                self.parent[self.known]['']['st_nlink'] += 1

        # update time for known tags that responded this time too
        confirmed_set = known_set.intersection(tag_set)
        for tag in confirmed_set:
            self.parent[self.known][tag]['st_mtime'] = time()

        if new_set or confirmed_set:
            self.parent[self.known]['']['st_mtime'] = time()

        # update directory time to reflect when changes occurred
        self['']['st_mtime'] = time()
        return 0


class ImageDirHandler(DirHandler):
    '''
    Software Images Directory Handler class

    Performs image directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(ImageDirHandler, self).__init__(a_dict)
        self.radio = radio

    def readdir(self, path_list):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list)
        tag_dir = im_get_dir(self.radio, path_list)
        if (tag_dir):
            # make set of versions found on tag
            tag_versions = []
            for version, state in tag_dir:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                              version=version,
                              state=str(state))
                if (str(state) != 'x'):
                    tag_versions.append('.'.join(map(str, version)))
            tag_set = Set(tag_versions)
            # make set of version founds on self
            my_versions = []
            for version in self.keys():
                if version is not '':
                    my_versions.append(version)
            my_set = Set(my_versions)
            self.log.info(method=inspect.stack()[0][3],
                          local=my_set,
                          tag=tag_set)

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

        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           dir=self)
        return super(ImageDirHandler, self).readdir(path_list)

    def create(self, path_list, mode):
        file_name = path_list[-1]
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list[:-1],
                      mode=oct(mode),
                      file=file_name)
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
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        del self[path_list[-1]]   # last element is version
        return 0

    def release(self, path_list): # close
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        return 0


class SysDirHandler(DirHandler):
    '''
    System Directory Handler class

    Performs 'tag/sys' directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysDirHandler, self).__init__(a_dict)
        self.radio = radio

    def readdir(self, path_list, img_state=''):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           path_list=path_list)
        tag_dir = im_get_dir(self.radio, path_list)
        if (tag_dir):
            # make set of versions found on tag
            tag_versions = []
            for version, state in tag_dir:
                if (img_state == '') or (img_state == state):
                    tag_versions.append('.'.join(map(str, version)))
            tag_set = Set(tag_versions)
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                               tag=tag_set)
            # make set of version founds on self
            my_versions = []
            for version in self.keys():
                if version is not '':
                    my_versions.append(version)
            my_set = Set(my_versions)
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               lineno=sys._getframe().f_lineno,
                               tag=my_set)

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
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           dir=self)
        return super(SysDirHandler, self).readdir(path_list)


class SysActiveDirHandler(SysDirHandler):
    '''
    System Active Directory Handler class

    Performs sys/active directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysActiveDirHandler, self).__init__(radio, a_dict)

    def link(self, ln_l, tg_l):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           local_name=ln_l,
                           target=tg_l)
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
            self[new_version] = SysFileHandler(self.radio,
                                        S_IFREG,
                                        0o664,
                                        1)
            self.log.info(method=inspect.stack()[0][3],
                          version=new_version)
            return 0
        self.log.warn('timeout', method=inspect.stack()[0][3],
                      version=new_version,
                      local_name=ln_l, target=tg_l)
        return 0

    def readdir(self, path_list):
        dir = super(SysActiveDirHandler, self).readdir(
            path_list, img_state='active')
        self.log.info(method=inspect.stack()[0][3], dir=dir)
        return dir

    def unlink(self, path_list):
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        return 0


class SysBackupDirHandler(SysDirHandler):
    '''
    System Backup Directory Handler class

    Performs backup directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysBackupDirHandler, self).__init__(radio, a_dict)

    def link(self, ln_l, tg_l):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           local_name=ln_l,
                           target=tg_l)
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
            self[new_version] = SysFileHandler(self.radio,
                                        S_IFREG,
                                        0o664,
                                        1)
            self.log.info(method=inspect.stack()[0][3],
                          version=new_version)
            return 0
        return 0

    def readdir(self, path_list):
        dir = super(SysBackupDirHandler, self).readdir(
                       path_list, img_state='backup')
        self.log.info(method=inspect.stack()[0][3], dir=dir)
        return dir

    def unlink(self, path_list):
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
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


class VerbosityDirHandler(DirHandler):
    '''
    Debug Verbosity Directory Handler class

    Set and get verbosity level using file system.
    '''
    def __init__(self, a_dict):
        super(VerbosityDirHandler, self).__init__(a_dict)
        self.file_name = str(get_cmd_args().verbosity)
        self[self.file_name] = FileHandler(S_IFREG, 0o444, 1)

    def create(self, path_list, mode):
        '''
        delete current setting and replace with new value
        '''
        file_name = path_list[-1]
        set_verbosity(int(file_name))
        if get_cmd_args().verbosity > 4:
            self.log.debug(method=inspect.stack()[0][3],
                           lineno=sys._getframe().f_lineno,
                           file=file_name,
                           mode=oct(mode),
                           path_list=path_list)
        del self[self.file_name]
        self[file_name] = FileHandler(S_IFREG, 0o444, 1)
        self.file_name=file_name
        self.log.warn('set verbosity',
                      method=inspect.stack()[0][3],
                      verbosity=get_cmd_args().verbosity,
                      path_list=path_list)
        return 0

taglog.debug('initiialization complete')

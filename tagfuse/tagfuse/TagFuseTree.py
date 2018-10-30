from __future__ import print_function, absolute_import, division

__all__ = ['TagFuseRootTree',
           'TagFuseTagTree']

import os
import sys
import structlog
logger = structlog.getLogger('fuse.log-mixin.' + __name__)
toplog = logger.bind(scope='global')

from collections import defaultdict, OrderedDict
import copy
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time

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
    # zzz print('*** tagfusetree path:')
    # zzz print('\n'.join(sys.path))

try:
    from taghandlers import *
except ImportError:
    from tagfuse.taghandlers import *

'''
The TagFuseTree function returns a tree consisting of a set directory
and file objects that represent the Tag's TagNet naming structure.
This tree contains objects that process the information presented
by a Tag through the TagNet protocol stack over the radio. The tree
provides the basic framework for associating code in a class to the
unique processing features of the tag. For instance, managing software
images requires special handling of the file names which are strings
converted from the TagNet Version type.

The DirHandler Class requires a list of directory and/or file objects
to be initialized.

FileHandler Class requires three file attributes to be initialized:

File Type:
  Specifies type of file, we use: S_IFDIR (directory), S_IF_REG (file)

File permissions:
  This is just like the Linux file permissions. There are three levels,
  owner, group, and world. The read/write/execute permissions are
  defined for each level. These are represented as three sets of three
  bits of any combination of the following values:
    Read is equivalent to    4
    Write is equivalent to   2
    Execute is equivalent to 1
  See documentation on 'chmod' to get more background.

Number of Links:
  Number of links to this node.
  For a directory, used to track the number of entries (including '.'
  and '..')
  For a file, typically 1. If a file is linked, then this number is
  increased by 1 for each independent link. (used to keep track of
  active and backup software images, for instance).

There are several classes and subclasses to handle Tag specific
processing.

The FileHandler Classes are based on the Python dictionary class which
is used to hold the file attributes as a set of key/value pairs.

The DirHandler Classes are based on the Python dictionary class which
is used to hold a set of names and class objects representing files
and/or directories. The dictionary keys are the file/directory names
and the values are another file or directory class. Every directory
has a key == '' to provide its file system attributes. This special
directory is not exposed to the outside world.

There are a set of subfunctions that are used to divide the tree up
for easier comprehension and maintainence.

There are two main functions:
TagFuseRootTree  toor the root of the overall structure, including
                 the test directories and all of the individual Tag
                 directories (which are dynamically added).
TagFuseTagTree   returns a new copy of the tree used for each Tag.
                 This needs to be versioned.
'''

def TagFusePollTree(radio):
    return DirHandler(OrderedDict([
        ('',        FileHandler(S_IFDIR, 0o751, 6)),
        ('cnt',     ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
        ('ev',      ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
    ]))

def TagFuseSysTree(radio):
    return DirHandler(OrderedDict([
        ('',        FileHandler(S_IFDIR, 0o751, 8)),
        ('rtc',     RtcFileHandler(radio, S_IFREG, 0o644, 1)),
        ('active',  SysActiveDirHandler(radio, OrderedDict([
            ('',      FileHandler(S_IFDIR, 0o775, 4)),]))
        ),
        ('backup',  SysBackupDirHandler(radio, OrderedDict([
            ('',      FileHandler(S_IFDIR, 0o775, 4)),]))
        ),
        ('golden',  SysGoldenDirHandler(radio, OrderedDict([
            ('',      FileHandler(S_IFDIR, 0o775, 4)),]))
        ),
        ('nib',     SysNibDirHandler(radio, OrderedDict([
            ('',      FileHandler(S_IFDIR, 0o775, 4)),]))
        ),
        ('running', SysRunningDirHandler(radio, OrderedDict([
            ('',      FileHandler(S_IFDIR, 0o775, 4)),]))
        ),
    ]))


def TagFuseSDTree(radio):
    return DirHandler(OrderedDict([
        ('',        FileHandler(S_IFDIR, 0o751, 6)),
        ('0',       DirHandler(OrderedDict([
            ('',      FileHandler(S_IFDIR, 0o751, 6)),
            ('img',   ImageDirHandler(radio, OrderedDict([
                ('',    FileHandler(S_IFDIR, 0o751, 4)),
            ]))),
            ('dblk',  DirHandler(OrderedDict([
                ('',     FileHandler(S_IFDIR, 0o751, 12)),
                ('byte',    SparseIOFileHandler(radio, S_IFREG, 0o444, 1)),
                ('note',    SimpleIORecHandler (radio, S_IFREG, 0o660, 1)),
                ('.recnum',   ByteIOFileHandler(radio, S_IFREG, 0o664, 1)),
                ('.last_rec', ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                ('.last_sync',ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                ('.committed',ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                ('.offset',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                ('.size',     ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                ('.resync',   ByteIOFileHandler(radio, S_IFREG, 0o664, 1)),
                ('filter',  DirHandler(OrderedDict([
                    ('',     FileHandler(S_IFDIR, 0o751, 2)),
                    ('include',  DirHandler(OrderedDict([
                        ('',     FileHandler(S_IFDIR, 0o751, 2)),
                        ('DT_EVENT',  DirHandler(OrderedDict([
                            ('',        FileHandler(S_IFDIR, 0o751, 2)),
                        ]))),
                    ]))),
                    ('exclude',  DirHandler(OrderedDict([
                        ('',     FileHandler(S_IFDIR, 0o751, 2)),
                        ('DT_EVENT',  DirHandler(OrderedDict([
                            ('',        FileHandler(S_IFDIR, 0o751, 2)),
                        ]))),
                    ]))),
                ])))
            ]))),
            ('panic', DirHandler(OrderedDict([
                ('',       FileHandler(S_IFDIR, 0o751, 4)),
                ('byte',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                ('.count', ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
            ]))),
        ]))),
    ]))

def TagFuseInfoTree(radio):
    return DirHandler(OrderedDict([
        ('',        FileHandler(S_IFDIR, 0o751, 3)),
        ('sens',    DirHandler(OrderedDict([
            ('',      FileHandler(S_IFDIR, 0o751, 3)),
            ('gps',   DirHandler(OrderedDict([
                ('',    FileHandler(S_IFDIR, 0o751, 4)),
                ('xyz', SimpleIORecHandler(radio, S_IFREG, 0o444, 1)),
                ('cmd', SimpleIORecHandler(radio, S_IFREG, 0o220, 1)),
            ]))),
        ]))),
    ]))

def TagFuseTagTree(radio):
    return DirHandler(OrderedDict([
        ('',        FileHandler(S_IFDIR, 0o751, 3)),
        ('tag',     DirHandler(OrderedDict([
            ('',       FileHandler(S_IFDIR, 0o751, 6)),
            ('poll',   TagFusePollTree(radio)),
            ('sd',     TagFuseSDTree(radio)),
            ('sys',    TagFuseSysTree(radio)),
            ('info',   TagFuseInfoTree(radio)),
            ('radio',  DirHandler(OrderedDict([
                ('',       FileHandler(S_IFDIR, 0o751, 7)),
                ('stats',  SimpleIORecHandler(radio, S_IFREG, 0o666, 1)),
            ]))),
            ('.test',   DirHandler(OrderedDict([
                ('',       FileHandler(S_IFDIR, 0o751, 7)),
                ('echo',   ByteIOFileHandler(radio, S_IFREG, 0o662, 1)),
                ('ones',   ByteIOFileHandler(radio, S_IFREG, 0o664, 1)),
                ('zeros',  ByteIOFileHandler(radio, S_IFREG, 0o664, 1)),
                ('sum',    ByteIOFileHandler(radio, S_IFREG, 0o664, 1)),
                ('drop',   ByteIOFileHandler(radio, S_IFREG, 0o662, 1)),
            ]))),
        ]))),
    ]))

def TagFuseRootTree(radio):
    return RootDirHandler(OrderedDict([
        ('',        FileHandler(S_IFDIR, 0o751, 4)),
        ('.test',   DirHandler(OrderedDict([
            ('',       FileHandler(S_IFDIR, 0o751, 6)),
            ('echo',   TestEchoHandler(S_IFREG, 0o666, 1)),
            ('ones',   TestOnesHandler(S_IFREG, 0o444, 1)),
            ('zeros',  TestZerosHandler(S_IFREG, 0o444, 1)),
            ('sum',    TestSumHandler(S_IFREG, 0o222, 1)),
        ]))),
        ('.verbosity', VerbosityDirHandler(OrderedDict([
            ('',       FileHandler(S_IFDIR, 0o751, 4)),
        ]))),
        ('.poll',   DirHandler(OrderedDict([
            ('',       FileHandler(S_IFDIR, 0o751, 6)),
            ('new1',   PollNetDirHandler(radio, 35, 'found', OrderedDict([
                ('',       FileHandler(S_IFDIR, 0o751, 4)),
            ]))),
            ('new5',   PollNetDirHandler(radio, 165, 'found', OrderedDict([
                ('',       FileHandler(S_IFDIR, 0o751, 4)),
            ]))),
            ('found', PollNetDirHandler(radio, 1, 'found', OrderedDict([
                ('',       FileHandler(S_IFDIR, 0o751, 4)),
            ]))),
        ]))),
        ('ffffffffffff', TagFuseTagTree(radio)),
    ]))

toplog.debug('initiialization complete')

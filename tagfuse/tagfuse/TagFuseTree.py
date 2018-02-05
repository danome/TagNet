from __future__ import print_function, absolute_import, division

import logging
import os
import sys

from collections import defaultdict, OrderedDict
import copy
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
                                            sys.argv[0],
                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [basedir,
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)

from taghandlers import *

'''
The TagFuseFileTree function returns a tree (really a dictionary
of dictionaries) which describes the contents of information
presented by the TagNet protocol stack in talking with a Tag
over the radio. It provides the basic framework for associating
unique processing step needed by the different features of the tag.
For instance, managing software images requires special handling of
the file names which are strings converted from the TagNet Version
type.

FileHandler Classes require three file attributes to be initialized:

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
'''

def TagFuseFileTree(radio):
    return PollNetDirHandler(radio, OrderedDict([
        ('',            FileHandler(S_IFDIR, 0o751, 3)),
        ('.test',        DirHandler(OrderedDict([
            ('',           FileHandler(S_IFDIR, 0o751, 6)),
            ('echo',       TestEchoHandler(S_IFREG, 0o666, 6)),
            ('ones',       TestOnesHandler(S_IFREG, 0o444, 6)),
            ('zeros',      TestZerosHandler(S_IFREG, 0o444, 6)),
            ('sum',        TestSumHandler(S_IFREG, 0o222, 6)),
        ]))),
        ('<node_id:ffffffffffff>', DirHandler(OrderedDict([
            ('',           FileHandler(S_IFDIR, 0o751, 6)),
            ('tag',        DirHandler(OrderedDict([
                ('',          FileHandler(S_IFDIR, 0o751, 4)),
                ('sd',        DirHandler(OrderedDict([
                    ('',        FileHandler(S_IFDIR, 0o751, 6)),
                    ('0',       DirHandler(OrderedDict([
                        ('',      FileHandler(S_IFDIR, 0o751, 6)),
                        ('img',   ImageDirHandler(radio, OrderedDict([
                            ('',    FileHandler(S_IFDIR, 0o751, 4)),
                        ]))),
                        ('dblk',  DirHandler(OrderedDict([
                            ('',     FileHandler(S_IFDIR, 0o751, 7)),
                            ('byte',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('note',    DblkIONoteHandler(radio, S_IFREG, 0o220, 1)),
                            ('.recnum',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('.last_rec', ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('.last_sync',ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                        ]))),
                        ('panic', DirHandler(OrderedDict([
                            ('',    FileHandler(S_IFDIR, 0o751, 4)),
                            ('byte',DirHandler(OrderedDict([
                                ('',    FileHandler(S_IFDIR, 0o751, 35)),
                                ('0',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                                ('1',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                                ('2',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                                ('3',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                                ('4',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ]))),
                        ]))),
                    ]))),
                ]))),
                ('sys',       DirHandler(OrderedDict([
                    ('',        FileHandler(S_IFDIR, 0o751, 7)),
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
                ]))),
                ('info',      DirHandler(OrderedDict([
                    ('',        FileHandler(S_IFDIR, 0o751, 4)),
                    ('sens',    DirHandler(OrderedDict([
                        ('',      FileHandler(S_IFDIR, 0o751, 4)),
                        ('gps',   DirHandler(OrderedDict([
                            ('',    FileHandler(S_IFDIR, 0o751, 4)),
                            ('xyz', FileHandler(S_IFREG, 0o660, 1)),
                            ('cmd', ByteIOFileHandler(radio, S_IFREG, 0o660, 1)),
                        ]))),
                    ]))),
                ]))),
            ]))),
        ]))),
    ]))

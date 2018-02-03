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

def TagFuseFileTree(radio):
    return PollNetDirHandler(radio, OrderedDict([
        ('',                       FileHandler(S_IFDIR, 0o751, 3)),
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

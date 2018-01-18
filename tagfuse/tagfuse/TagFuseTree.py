from __future__ import print_function, absolute_import, division

import logging
import os
from collections import defaultdict, OrderedDict
import copy
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time

from taghandlers import *

def TagFuseFileTree(radio):
    return DirHandler(OrderedDict([
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
                        ('',     FileHandler(S_IFDIR, 0o751, 4)),
                        ('byte',   DirHandler(OrderedDict([
                            ('',     FileHandler(S_IFDIR, 0o751, 3)),
                            ('0',    ByteIOFileHandler(radio, S_IFREG, 0o220, 1)),
                        ]))),
                        ('note',    DblkIONoteHandler(radio, S_IFREG, 0o220, 1)
                        )
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
                            ('5',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('6',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('7',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('8',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('9',   ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('10',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('11',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('12',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('13',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('14',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('15',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('16',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('17',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('18',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('19',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('20',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('21',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('22',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('23',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('24',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('25',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('26',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('27',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('28',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('29',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('30',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                            ('31',  ByteIOFileHandler(radio, S_IFREG, 0o444, 1)),
                        ]))),
                    ]))),
                ]))),
            ]))),
            ('sys',       DirHandler(OrderedDict([
                ('',        FileHandler(S_IFDIR, 0o751, 7)),
                ('active',  SysActiveDirHandler(radio, OrderedDict([
                    ('',      FileHandler(S_IFDIR, 0o751, 4)),]))
                ),
                ('backup',  SysBackupDirHandler(radio, OrderedDict([
                    ('',      FileHandler(S_IFDIR, 0o751, 4)),]))
                ),
                ('golden',  SysGoldenDirHandler(radio, OrderedDict([
                    ('',      FileHandler(S_IFDIR, 0o751, 4)),]))
                ),
                ('nib',     SysNibDirHandler(radio, OrderedDict([
                    ('',      FileHandler(S_IFDIR, 0o751, 4)),]))
                ),
                ('running', SysRunningDirHandler(radio, OrderedDict([
                    ('',      FileHandler(S_IFDIR, 0o751, 4)),]))
                ),
            ]))),
            ('info',      DirHandler(OrderedDict([
                ('',        FileHandler(S_IFDIR, 0o751, 4)),
                ('sens',    DirHandler(OrderedDict([
                    ('',      FileHandler(S_IFDIR, 0o751, 4)),
                    ('gps',   DirHandler(OrderedDict([
                        ('',    FileHandler(S_IFDIR, 0o751, 4)),
                        ('xyz', FileHandler(S_IFREG, 0o660, 1)),
                    ]))),
                ]))),
            ]))),
        ]))),
    ]))

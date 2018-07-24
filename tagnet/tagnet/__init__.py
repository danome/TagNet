"""
Tagnet: Native Python implementation for Tagnet Protocol

@author: Dan Maltbie
"""

import os,sys
# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.abspath(os.getcwd())
# zzz print('tagnet: ', sys.argv[0], basedir)
if (os.path.exists(os.path.join(basedir, 'setup.py')) and
    os.path.exists(os.path.join(basedir, 'tagnet'))):
    sys.path.insert(0, os.path.join(basedir, 'tagnet'))
    print '\n'.join(sys.path)

__version__ = '0.1.4'
print 'TagNet Driver Version {}'.format(__version__)

from .tagnames import *
from .tagmessages import *
from .tagdef import *
from .tagtlv import *

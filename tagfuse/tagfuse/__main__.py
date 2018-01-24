"""
tagfuse:  FUSE Filesystem for accessing Tag Storage

@author: Dan Maltbie, (c) 2017
"""

import os
import sys

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
                                            sys.argv[0],
                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('\n'.join(sys.path))

from tagfuse     import TagStorage
from tagfuseargs import parseargs

def main():
    TagStorage(parseargs())

if __name__ == '__main__':
    main()

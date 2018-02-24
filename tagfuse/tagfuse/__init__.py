"""
Tagnet: TagNet Fuse Filesystem for accessing Tag Storage

@author: Dan Maltbie, (c) 2017
"""
import os
import sys

__version__ = '0.0.10'

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# zzz print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
# zzz                                           sys.argv[0],
# zzz                                           basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('\n'.join(sys.path))

__all__ = ['sparsefile',
           'radioutils',
           'radioimage',
           'radiofile',
           'taghandlers',
           'TagFuseTree',
           'tagfuseargs',
           '__main__',
]
print('*** __init__.py','ending')

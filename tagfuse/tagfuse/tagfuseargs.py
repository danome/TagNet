import os
import sys
import argparse

# If we are running from the source package directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('\n'.join(sys.path))

from __init__ import __version__ as VERSION
print('tagfuse version: ', VERSION)

def parseargs():
    parser = argparse.ArgumentParser(
        description='Tagnet FUSE Filesystem driver v{}'.format(VERSION))
    parser.add_argument('mountpoint',
                        help='directory To Be Used As Mountpoint')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s ' + VERSION)
    # 0v print errors
    # v  also print entr/exit info
    # vv also print execution info
    parser.add_argument('-v', '--verbosity',
                        action='count',
                        default=1,
                        help='increase output verbosity')
    return parser.parse_args()

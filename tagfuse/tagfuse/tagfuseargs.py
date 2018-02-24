import os
import sys
import argparse

__version__ = '0.0.17'
print('tagfuse version: ', __version__)
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

def parseargs():
    parser = argparse.ArgumentParser(
        description='Tagnet FUSE Filesystem driver v{}'.format(__version__))
    parser.add_argument('mountpoint',
                        help='directory To Be Used As Mountpoint')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s ' + __version__)
    # 0v print errors
    # v  also print entr/exit info
    # vv also print execution info
    parser.add_argument('-v', '--verbosity',
                        action='count',
                        default=1,
                        help='increase output verbosity')
    args = parser.parse_args()
    if args.verbosity:
        print("verbosity turned on", args.verbosity)
    return args

print('*** tagfuseargs.py','ending')

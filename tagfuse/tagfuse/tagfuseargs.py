import os
import sys
import argparse

__version__ = '0.0.31'

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

__all__ = ['process_cmd_args', 'get_cmd_args']

#
# global_args    provides a global source for the processed command line
#                variabls, such as directory name of mount point and where
#                to put sparse filesas well as verbosity
#
global_args = None

def full_path(dir_):
    if dir_[0] == '~' and not os.path.exists(dir_):
        dir_ = os.path.expanduser(dir_)
    return os.path.abspath(os.path.realpath(dir_))

class expand_pathname(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
       setattr(namespace, self.dest, full_path(values))


def process_cmd_args():
    global global_args

    parser = argparse.ArgumentParser(
        description='Tagnet FUSE Filesystem driver v{}'.format(__version__))
    parser.add_argument('mountpoint',
                        action=expand_pathname,
                        help='directory To Be Used As Fuse Mountpoint')
    parser.add_argument('-s', '--sparse_dir',
                        default='/tmp',
                        help='directory where sparsefiles are stored')
    parser.add_argument('--disable_sparse',
                        action='store_true',
                        default=False,
                        help='disable sparse file storage')
    parser.add_argument('--disable_sparse_read',
                        action='store_true',
                        default=False,
                        help='disable sparse read (but still write)')
    parser.add_argument('-b', '--background',
                        action='store_true')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='tagfuse: ' + __version__)
    # 0v print errors
    # v  also print entr/exit info
    # vv also print execution info
    parser.add_argument('-v', '--verbosity',
                        action='count',
                        default=1,
                        help='increase output verbosity')
    # nifty way to set a default value
    # parser.set_defaults(feature=True)

    global_args = parser.parse_args()

    print("mountpoint", global_args.mountpoint)
    if global_args.verbosity:
        print("verbosity turned on", global_args.verbosity)
    global_args.sparse_dir = full_path(global_args.sparse_dir)
    print("sparse files stored here", global_args.sparse_dir)

    return global_args


def get_cmd_args():
    global global_args
    return global_args

# print('*** tagfuseargs.py','ending')

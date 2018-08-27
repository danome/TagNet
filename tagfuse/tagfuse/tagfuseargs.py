import os
import sys
import argparse
import time
import logging
import structlog
import inspect

from myversion import __version__

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

__all__ = ['process_cmd_args', 'get_cmd_args', 'set_verbosity', 'taglog', 'rootlog']

import tagnet
import si446x


'''
global_args     provides a global source for the processed command line
                variabls, such as directory name of mount point and where
                to put sparse filesas well as verbosity
'''
global_args = None

'''
rootlog         structlog logger of base fuse class

taglog          structlog logger of tagfuse modules
'''
rootlog     = None
taglog      = None


#
# helper routines
#
def full_path(dir_):
    if dir_[0] == '~' and not os.path.exists(dir_):
        dir_ = os.path.expanduser(dir_)
    return os.path.abspath(os.path.realpath(dir_))

class expand_pathname(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
       setattr(namespace, self.dest, full_path(values))



def set_verbosity(n):
    '''
    # 0  fuse warn,  tagfuse warn
    # 1  fuse info,  tagfuse info
    # 2  fuse info,  tagfuse debug
    # 3  fuse info,  tagfuse debug
    # 4+ fuse debug, tagfuse debug
    '''
    global global_args, rootlog, taglog
    global_args.verbosity = int(n)
    print('set_verbosity', n)
    if global_args.verbosity > 3:
        rootlog.setLevel(logging.DEBUG)
        taglog.setLevel(logging.DEBUG)
        taglog.warn('>3',method=inspect.stack()[0][3],
                   verbosity=n)
    elif global_args.verbosity == 3:
        rootlog.setLevel(logging.INFO)
        taglog.setLevel(logging.DEBUG)
        taglog.warn('=3',method=inspect.stack()[0][3],
                   verbosity=n)
    elif global_args.verbosity == 2:
        rootlog.setLevel(logging.INFO)
        taglog.setLevel(logging.DEBUG)
        taglog.warn('=2',method=inspect.stack()[0][3],
                   verbosity=n)
    elif global_args.verbosity == 1:
        rootlog.setLevel(logging.INFO)
        taglog.setLevel(logging.INFO)
        taglog.warn('=1',method=inspect.stack()[0][3],
                   verbosity=n)
    else:                       # == 0:
        rootlog.setLevel(logging.WARNING)
        taglog.setLevel(logging.WARNING)
        taglog.warn('=0',method=inspect.stack()[0][3],
                   verbosity=n)

def add_handlers(log):
    # logging format control
    #
    global global_args
    logging.Formatter.converter = time.gmtime
    fmt_console = logging.Formatter( '--- %(name)-22s %(message)s' )
    fmt_file    = logging.Formatter(
        '--- %(asctime)s (%(levelname)s) %(name)-22s - %(message)s' )
    try:
        console = logging.StreamHandler()
        console.setFormatter(fmt_console)
        log.addHandler(console)

        # need to verfiy that rotating files work correctly
        # logfile = logging.RotatingFileHandler(
        #    global_args.logfile, maxBytes=100000000, backupCount=3)

        logfile = logging.FileHandler(global_args.logfile)
        logfile.setFormatter(fmt_file)
        log.addHandler(logfile)

    except (ValueError, TypeError) as e:
        log.error('failed to install logging formatters', error=e)
        sys.exit()

def configure_logging():
    # structured logging configuration
    #
    global global_args, rootlog, taglog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            # structlog.processors.StackInfoRenderer(),
            structlog.stdlib.PositionalArgumentsFormatter(),
            # structlog.processors.TimeStamper(fmt='%Y-%m-%d %H:%M.%S'),
            structlog.processors.KeyValueRenderer(key_order=['event',
                                                             'scope',
                                                             'method',],
                                                  drop_missing=True),
            # structlog.processors.JSONRenderer(),
            # xxx structlog.stdlib.add_logger_name,
            # structlog.stdlib.add_log_level,
            # structlog.processors.UnicodeDecoder(),
            # structlog.processors.StackInfoRenderer(),
            # structlog.processors.format_exc_info,
            # xxx structlog.stdlib.render_to_log_kwargs,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # set up logging infrastructure. there are two distinct
    #loggers, one for the base fuse class and a second one for
    # the tagfuse code. They are separate so that the logging
    # level can be controlled separately, thus limiting the
    # noise of the base fuse class when it is not needed.
    #
    rootlog = structlog.getLogger('fuse.log-mixin')
    add_handlers(rootlog)
    taglog = structlog.getLogger('fuse.log-mixin.tagfuse')
    set_verbosity(global_args.verbosity)


def process_cmd_args():
    global global_args, taglog, rootlog
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
    parser.add_argument('--logfile',
                        default='/tmp/tagfuse.log',
                        help='log filename')
    parser.add_argument('--disable_sparse_read',
                        action='store_true',
                        default=False,
                        help='disable sparse read (but still write)')
    parser.add_argument('-b', '--background',
                        action='store_true')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='tagfuse: ' + __version__)
    parser.add_argument('-v', '--verbosity',
                        action='count',
                        default=0,
                        help='increase output verbosity')
    # nifty way to set a default value
    # parser.set_defaults(feature=True)

    global_args = parser.parse_args()

    # expand path for sparse directory
    global_args.sparse_dir = full_path(global_args.sparse_dir)

    configure_logging()
    mylog = structlog.getLogger('fuse.log-mixin.tagfuse.' + __name__)
    mylog.warn(version={'tagfuse':__version__, 'tagnet':tagnet.__version__, 'si446x':si446x.__version__})
    mylog.warn(logfile=global_args.logfile,
               mountpoint=global_args.mountpoint,
               verbosity=global_args.verbosity,
               sparse_dir=format(global_args.sparse_dir))
    mylog.debug('initialization complete')
    return global_args


def get_cmd_args():
    global global_args
    return global_args

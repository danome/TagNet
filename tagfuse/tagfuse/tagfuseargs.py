from __init__ import __version__ as VERSION
import argparse
def parseargs():
    parser = argparse.ArgumentParser(
        description='Tagnet FUSE Filesystem driver v{}'.format(VERSION))
    parser.add_argument('mountpoint',
                        type=argparse.FileType('rb'),
                        help='directory To Be Used As Mountpoint')
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s ' + VERSION)
    parser.add_argument('--rtypes',
                        type=str,
                        help='output records matching types in list')
    parser.add_argument('-f', '--first_sector',
                        type=int,
                        help='begin with START_SECTOR')
    # 0v print record details, suppress recoverable errors
    # v  also print the record header and all errors
    # vv also print the record buffer
    parser.add_argument('-v', '--verbosity',
                        action='count',
                        default=1,
                        help='increase output verbosity')
    return parser.parse_args()

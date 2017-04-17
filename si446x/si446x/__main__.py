from si446xdvr           import reactor_loop
from twisted.python      import log
import sys

from si446xvers          import __version__

print 'si446x driver version {}'.format(__version__)

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    log.msg("si446x Driver Version: %s"%(__version__))
    reactor_loop()



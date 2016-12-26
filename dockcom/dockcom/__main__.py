from dockcomdvr           import reactor_loop
from twisted.python      import log
import sys

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    reactor_loop()

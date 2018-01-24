from si446xdvr           import reactor_loop
from twisted.python      import log
import sys

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.abspath(os.getcwd())
print('Si446xDevice: ', sys.argv[0], basedir)
if (os.path.exists(os.path.join(basedir, 'setup.py')) and
    os.path.exists(os.path.join(basedir, 'si446x'))):
    sys.path.insert(0, os.path.join(basedir, 'si446x'))
    print(os.sys.path)

from si446xvers          import __version__

print 'si446x driver version {}'.format(__version__)

def main():
    log.startLogging(sys.stdout)
    log.msg("si446x Driver Version: %s"%(__version__))
    reactor_loop()

if __name__ == '__main__':
    main()

"""
tagfuse:  FUSE Filesystem for accessing Tag Storage

@author: Dan Maltbie, (c) 2017
"""

#from tagfuseargs import parseargs

def main(argv):
    from tagfuse import TagStorage
    print(argv)
    TagStorage(argv)

if __name__ == '__main__':
    from sys import argv
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)
    main(argv)

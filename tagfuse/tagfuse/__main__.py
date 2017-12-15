"""
tagfuse:  FUSE Filesystem for accessing Tag Storage

@author: Dan Maltbie, (c) 2017
"""
#print('tagfuse/__main__.py executed')

from tagfuse import storage
from tagfuseargs import parseargs

def main():
    storage(parseargs())

if __name__ == '__main__':
    main()

# TagNet

Dan Maltbie <dmaltbie@daloma.org>
v1.1, March 2018

*License*: [MIT](http://www.opensource.org/licenses/mit-license.php)

## Introduction

## Directory Contents

Usage Example
-------------
### Direct_io read is accessed in the following way:
```
f = os.open('foo/dblk/0',  os.O_DIRECT | os.O_RDONLY)
buf = os.read(f, 10)
os.lseek(f, fpos, 0)
fpos = os.lseek(f, 0, 1)  # returns current file position
```

* Running tagfuse from development directory

zot: cd <dev_home>/Tagnet/tagfuse
zot: python -m tagfuse ~/tag/tag01

this will run the development package tagfuse (the directory containing
all the python source) as a module, on the mount point ~/tag/tag01.

* running a development install

zot: cd <dev_home>/Tagnet/tagfuse
zot: sudo ./setup.py develop


This will install tagfuse using setup/ezinstall links.

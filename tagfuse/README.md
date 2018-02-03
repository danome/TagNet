# TagNet

Dan Maltbie <dmaltbie@daloma.org>
v1.0, July 2016

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

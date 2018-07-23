# Overview

Tag and Basestation.

General model of use.

Paradigm of Unix filesystem.


# Basestation

The TagNet Basestation provides the control and monitoring services for the network of tags.

This includes:
- Initial setup and pairing of new tags
- Detection and monitoring of live tags
- Data collection and storage from tags
- Software updates of tags

The Basestation consists of a Raspberry Pi running Raspian Linux and the TagNet Software.

The Basestation TagNet software, called TagFuse, exposes access and control of tags by providing a filesystem interface to all tag data based on the FUSE Filesystem. FUSE provides an API for implementating the Linux file I/O operations from within a user space program. FUSE is used for many different applications and is a very stable and well understood solution.

The TagFuse application runs as a background task and is accessed through the standard linux filesystem. When started, TagFuse establishes a mountpoint in the filesystem from which all tag related data can be accessed. Any existing Linux application can access a tag data as a 'file' within the TagFuse subdirectories.

The top level of the Tagfuse filesystem shows all tags that are currently within range of the Basestation. Each tag is identified by its Node Identifier, a factory set value that uniquely identifies a tag from all others. The identifier can also be found on a physical label attached to the tag.
'''
/root/TagFuse/045A634E91B6
'''

Below each tag idenfier is a set of sub-directories that expose the data within the tag.

This includes:
- the data on the tag's internal sd card, which holds the data log and the software images
- access to all live sensor readings
- system variables for configuring and controlling the tag operation

Below is an example of the sub-directories that may be found on tag.
```
root
+-- <nodeid:000000000000>
    +-- tag
        |-- poll
        |   |-- cnt
        |   +-- ev
        |
        |-- info
        |   +-- sens
        |       +-- gps
        |           +-- xyz
        |-- sd
        |   +-- 0
        |       |-- dblk
        |       |   |-- byte
        |       |   +-- note
        |       |-- img
        |       +-- panic
        |           +-- byte
        +-- sys
            |-- active
            |-- backup
            |-- golden
            |-- nib
            |-- rtc
            +-- running
```


# Functionality
## Unix Filesystem Basics
The model used to describe access a Tag's data leverages the Unix paradigm for organizing data into files that can be grouped in directories of directories. This simplifies the programming model, leveraging Unix fundamentals like pipes and file redirection.

The TagFuse Driver provides access to a Tag's data using file system operations like open, close, read, and write. For instance, to access the Tag's main store of logging information, the Dblk file, one would read the ```/<tagid>/tag/sd/0/dblk/byte``` file. A small message can be added to the Dblk file by writing to the ```/<tagid>/tag/sd/0/dblk/note``` file. Standard Unix Coreutils (cp, ls, cat, echo, ...) can operate on any file in the TagFuse directory.

Furthermore, Python provides two main ways that file data can be transferred: buffered and direct. The buffered mode used the standard Unix VFS file system for data caching. In the buffered mode, data is cached by the operating system in large (4KByte) chunks. The cache is maintained as long as the file remains open. In direct mode, data is transferred on demand in whatever size is of interest.

Linux maintains some housekeeping formation about open files, such as the current file position (offset) as well as dilw descriptor attributes. Read and write calls at the Fuse driver level have both the size and the offset specified. Note that there are different seek operations for buffered and direct i/o modes.

The network protocol maintains stateless operation with each message specifying not only the file name by the file position and amount of data in transfer.

## Node directory and Polling for Tags
The easiest way to find out which Tags this Basestation knows about is to look in the TagFuse Root directory. you should see something like:
```
ls -al ~/tags
1a346563dc43    1dc58a235bd0      ffffffffffff
```
To discover new Tags a special directory named ```.poll``` is provided to iniatate the Tag polling sequence. This sequence is designed to wake up Tags that are dormant but may be waiting to communicate with the Basestation.

To initiate a poll for Tags, do the following:
```
ls ~/tags/.poll
```
This will take some time to complete since the Tags are in power saving mode and are a bit drowsy and non-responsive.

## Examining Sensor data
## Reading and Writing SD Card Storage
### Types of Storage
#### The Datablock
Contains typed data records.

File size is continually updated as more records are written to the SD Card.

Random seek


#### Software Images
Up to four Software Images can be stored on the Tag's SD Card. Images are identified by unique version numbers.

A new image can be transferred from the base to the Tag's SD Card by copying an appropriately packaged software image file to `../dblk/byte` [ where `../` refers to the path starting at the fuse mountpoint (aka root)].

Once an image has been successfully transferred, it will be listed in the `../img` directory as it's version (eg, `0.1.1`).

In order to have the Tag run a specific version of software, the user must set the system active version. The currently active version, if one exists, will automatically become the backup version. An image can also be assigned as the backup version. The system software replaces an active image with the  backup if excessive failures occur.

See Monitor and Control Operations below for how to set the Tag's active and backup software versions.
#### Panic Dumps
A copy of all available panic dumps (up to 32) can be made by copying from the dump file path `../panic/byte` to a file local to the Basestation.

Special software software is required to interpret the Panic Dump.

## Monitor and Control Tag Operation
Various controls are provided to monitor the operation of the Tag as well as control it.

The `../sys/` directory holds a set of directories identifying operational software image versions. Each directory may  contain a link to the software image in `../img/`.

The set of `../sys/` directories includes:
- Active   = the version of software to be loaded from SD Card to the Processor Flash Memory.
             Can be set to new version by linking to the specific file in the `../img/` directory.
- Backup   = the version of software to be loaded should the Active image fail to be stable.
             Can be set to new version by linking to the specific file in the `../img/` directory.
- Golden   = the version of software loaded in the Golden area of the Processor Flash Memory.
             Factory written version. Not user field programmable.
- NIB      = the version of software loaded in the NIB area of the Processor Flash memory.
             Should be the same as Active, but may vary if operational state is changing.
- Running  = the version of software currently running. Should be same as one of Golden or NIB.

NOTE: For the files under the 'golden', 'nib', and 'running' directories,  writing the ascii version string ('major.minor.build') of that file to that file will cause the Tag to reboot and begin running the specified version. The writing of the version is a protection against accidentally writing to the file and causing an erroneous reboot.

## Realtime Clock (RTC)
Check current time of Tag.
```
> stat sys/rtc
  File: sys/rtc
  Size: 0           Blocks: 0          IO Block: 512    regular empty file
Device: 21h/33d	Inode: 6           Links: 1
Access: (0644/-rw-r--r--)  Uid: ( 1000/      pi)   Gid: ( 1000/      pi)
Access: 2018-07-21 00:01:01.471811056 -0700
Modify: 2018-07-21 00:01:00.850250005 -0700
Change: 2018-07-20 23:58:42.958070039 -0700
```
Update Tag's time with Basestation current time.
```
touch sys/rtc
```
Can also set the time to a specific value
```
```
# Installation
## Linux and Python Package Prerequisites
Install the Si446x Radio Python Package. The executables are
placed in `/usr/local/lib/python2.7/dist-packages`.
```
cd TagNet/si446x
sudo ./setup.py install
```

```
cd TagNet/tagnet
sudo ./setup.py install
```
## TagFuse Installation
Install the TagFuse driver software from the TagNet Github
Repository at ```https://github.com/MamMark/TagNet```.

```
git clone https://github.com/MamMark/TagNet.git
cd TagNet/tagfuse
sudo ./setup.py install
cd ../tagnet
sudo ./setup.py install
cd ../si446x
sudo ./setup.py install
```
## Options
The TagFuse Driver supports the following options:
```
dvt6 (183): python tagfuse --help
TagNet Fuse Driver version: 0.2.2
usage: tagfuse [-h] [-s SPARSE_DIR] [--disable_sparse] [--disable_sparse_read]
               [-b] [-V] [-v]
               mountpoint

Tagnet FUSE Filesystem driver v0.2.2

positional arguments:
  mountpoint            directory To Be Used As Fuse Mountpoint

optional arguments:
  -h, --help            show this help message and exit
  -s SPARSE_DIR, --sparse_dir SPARSE_DIR
                        directory where sparsefiles are stored
  --disable_sparse      disable sparse file storage
  --disable_sparse_read
                        disable sparse read (but still write)
  -b, --background
  -V, --version         show program's version number and exit
  -v, --verbosity       increase output verbosity
```
# Operation
## Startup TagFuse Driver
```
tagfuse -b <tagfuse_mountpoint>
```
## Shutdown TagFuse Driver
```
fuser -u <tagfuse_mountpoint>
```
## Common Commands and Usage
### Get Dblk File related sizes and offsets
Various dblk sizes and offsets can be determined by examining
the file sizes on files in the `dblk/` directory:
- byte        number of bytes written to the dblk file
- .recnum     number of records in dblk file
- .last_rec   offset of last record of dblk file
- .last_sync  offset of last SYNC record of dblk file
- note        number of notes written
```
ls -al tags/1dc58a235bd0/tag/sd/0/dblk/
```
Output looks like this.
```
total 0
drwxr-x--x 7 root root        0 Feb  2 16:12 .
drwxr-x--x 5 root root        0 Feb  2 16:12 ..
-r--r--r-- 1 root root 99522048 Feb  2 16:17 byte
-r--r--r-- 1 root root 99523932 Feb  2 16:17 .last_rec
-r--r--r-- 1 root root 99521656 Feb  2 16:17 .last_sync
--w--w---- 1 root root      143 Feb  2 16:17 note
-r--r--r-- 1 root root   731884 Feb  2 16:17 .recnum
```
### Dblk file data
Get byte data from the Dblk File.
```
hexdump -s 512 -n 512 tags/1dc58a235bd0/tag/sd/0/dblk/byte
```
Output looks like this.
```
0000200 0080 0001 0001 0000 00e8 0000 0000 0000
0000210 1458 0000 4448 2000 ff30 2000 0000 0000
0000220 00ef dedf 000c 0000 0000 0000 faba faba
0000230 0000 0000 0000 0000 0000 0000 0001 0000
0000240 0000 0000 ffff ffff 0000 0000 0000 0000
0000250 0000 0000 0000 0000 faba faba 0000 0100
0000260 0005 0000 0000 0000 0000 0000 0000 0000
0000270 0000 0000 0000 0000 0000 0000 faba faba
0000280 00a8 0002 0002 0000 00e8 0000 0000 0000
0000290 0563 0000 0000 0000 5401 3327 0000 0000
00002a0 c1c4 0001 0000 0000 0000 0000 01a6 0002
00002b0 0000 0000 0000 0000 0000 0000 0000 0000
*
00003e0 0112 1300 b3b0 0000 0028 0004 0008 0000
00003f0 0563 0000 0000 0000 0209 0006 00e9 0000
0000400
```
### Dblk Notes
Write out a short note (up to 200 characters) to the dblk file
```
echo 'this is a test' > tags/1dc58a235bd0/tag/sd/0/dblk/note
```
Check to see how many notes have been written
```
ls -l tags/1dc58a235bd0/tag/sd/0/dblk/note
```
Output looks like this.
```
--w--w---- 1 root root 143 Feb  2 16:13 tags/1dc58a235bd0/tag/sd/0/dblk/note
```

### Load Software Image
```
dd if=<source_file> of=tags/1dc58a235bd0/tag/sd/0/img/x.x.x status=progress
```

### Activate a Software Image
Causes system reboot.
```
```
### Remove Software Image
Can't remove active image.
```
```

### Other
#### Show entire tree of information for a specific Tag
```
: tree -aphDA 658bc8e5205c/
658bc8e5205c/
└── [drwxr-x--x    0 Dec 31  1969]  tag
    ├── [drwxr-x--x    0 Dec 31  1969]  info
    │   └── [drwxr-x--x    0 Dec 31  1969]  sens
    │       └── [drwxr-x--x    0 Dec 31  1969]  gps
    │           ├── [--w--w----    0 Jul 21  0:07]  cmd
    │           └── [-r--r--r--    0 Dec 31  1969]  xyz
    ├── [drwxr-x--x    0 Dec 31  1969]  poll
    │   ├── [-r--r--r--    3 Jul 21  0:07]  cnt
    │   └── [-r--r--r--    3 Jul 21  0:07]  ev
    ├── [drwxr-x--x    0 Dec 31  1969]  sd
    │   └── [drwxr-x--x    0 Dec 31  1969]  0
    │       ├── [drwxr-x--x    0 Dec 31  1969]  dblk
    │       │   ├── [-r--r--r-- 1.2M Jul 21  0:07]  byte
    │       │   ├── [-r--r--r-- 1.2M Jul 21  0:07]  .committed
    │       │   ├── [-r--r--r-- 1.2M Jul 21  0:07]  .last_rec
    │       │   ├── [-r--r--r-- 1.2M Jul 21  0:07]  .last_sync
    │       │   ├── [-rw-rw----    0 Jul 21  0:07]  note
    │       │   └── [-r--r--r-- 2.6K Jul 21  0:07]  .recnum
    │       ├── [drwxr-x--x    0 Dec 31  1969]  img
    │       │   ├── [-rw-rw-r--    0 Jul 21  0:07]  0.2.9999
    │       │   ├── [-rw-rw-r--    0 Jul 21  0:07]  0.4.1
    │       │   └── [-rw-rw-r--    0 Jul 21  0:07]  0.4.2
    │       └── [drwxr-x--x    0 Dec 31  1969]  panic
    │           ├── [-r--r--r-- 2.3M Jul 21  0:07]  byte
    │           └── [-r--r--r--    0 Dec 31  1969]  .count
    ├── [drwxr-x--x    0 Dec 31  1969]  sys
    │   ├── [drwxrwxr-x    0 Dec 31  1969]  active
    │   │   └── [-rw-rw-r--    0 Jul 21  0:07]  0.4.1
    │   ├── [drwxrwxr-x    0 Dec 31  1969]  backup
    │   │   └── [-rw-rw-r--    0 Jul 21  0:07]  0.4.2
    │   ├── [drwxrwxr-x    0 Dec 31  1969]  golden
    │   │   └── [-rw-rw-r--    0 Jul 21  0:07]  0.4.0
    │   ├── [drwxrwxr-x    0 Dec 31  1969]  nib
    │   │   └── [-rw-rw-r--    0 Jul 21  0:07]  0.4.1
    │   ├── [-rw-r--r--    0 Jul 21  0:07]  rtc
    │   └── [drwxrwxr-x    0 Dec 31  1969]  running
    │       └── [-rw-rw-r--    0 Jul 21  0:07]  0.4.1
    └── [drwxr-x--x    0 Dec 31  1969]  .test
        ├── [--w--w--w-    0 Jul 21  0:08]  drop
        ├── [-rw-rw-rw-    0 Jul 21  0:07]  echo
        ├── [-r--r--r--    0 Jul 21  0:07]  ones
        ├── [--w--w--w-    0 Dec 31  1969]  sum
        └── [-r--r--r--    0 Dec 31  1969]  zeros

17 directories, 26 files
```

# Errorcodes
## TagNet Application Errorcodes
## Linux File System Errorcodes

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
            +-- running
```


# Functionality
## Unix Filesystem Basics
Leverage the Unix paradigm for organizing data into files that can be grouped in directories of directories.

This simplies the programming model, with many programs operating in a 'streaming' mode of operation.

Python provides to main ways that file data can be transferred: buffered and direct.

In the buffered mode, data is cached by the operating system in large (4KByte) chunks. The cache is maintained as long as the file remains open.

In direct mode, data is transferred on demand in whatever size is of interest.

Linux maintains some housekeeping formation about open files, such as the current file position (offset) as well as dilw descriptor attributes.

The network protocol maintains stateless operation with each message specifying not only the file name by the file position and amount of data in transfer.

## Node directory and Polling for Tags
## Examining Sensor data
## Reading and Writing SD Card Storage
### Types of Storage
#### The Datablock
Contains typed data records.

File size is continually updated as more records are written to the SD Card.

Random seek


#### Software Images
Up to four Software Images can be stored on the Tag's SD Card. Images are identified by unique version numbers.

A new image can be transferred from the base to the Tag's SD Card by copying an appropriately packaged software image file to `../dblk/byte/0` [ where `../` refers to the path starting at the fuse mountpoint (aka root)].

Once an image has been successfully transferred, it will be listed in the `../img` directory as it's version (eg, `0.1.1`).

In order to have the Tag run a specific version of software, the user must set the system active version. The currently active version, if one exists, will automatically become the backup version. An image can also be assigned as the backup version. The system software replaces an active image with the  backup if excessive failures occur.

See Monitor and Control Operations below for how to set the Tag's active and backup software versions.
#### Panic Dumps
Up to 32 Panic Dumps can be stored on the Tag's SD Card.

A copy of a panic dump can be made by copying from the dump file path `../panic/byte/0` to a file local to the Basestation.

Requires additional software to interpret the Panic Dump.
## Monitor and Control Tag Operation
Various controls are provided to monitor the operation of the Tag as well as control it.

The `../sys/` directory holds a set of directories identifying operational software image versions. Each directory may  contain a link to the software image in `../img/`.

The set of `../sys/` directories includes:
- Active   = the version of software to be loaded from SD Card to the Processor Flash Memory.
             Can be set to new version by linking to the specific file in the `../img/` directory.
- Backup   = the version of software to be loaded should the Active image fail to be stable.
             Can be set to new version by linking to the specific file in the `../img/` directory.
- Golden   = the version of software loaded in the Golden area of the Processor Flash Memory.
- NIB      = the version of software loaded in the NIB area of the Processor Flash memory.
             Should be the same as Active, but may vary if operational state is changing.
- Running  = the version of software currently running. Should be either Golden or NIB.

For the files under the 'golden', 'nib', and 'running' directories,  writing the ascii version string ('major.minor.build') of that file to that file will cause the Tag to reboot and begin running the specified version. The writing of the version is a protection against accidentally writing to the file and causing an erroneous reboot.

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
```
cd TagNet/tagfuse
sudo ./setup.py tagfuse <fuse_mountpoint>
```
## Options

# Operation
## Startup
```
cd TagNet/tagfuse
sudo ./setup.py tagfuse <tagfuse_mountpoint>
```
## Shutdown
```
fuser -u <tagfuse_mountpoint>
```
## Common Commands
### Get Dblk File related sizes and offsets
Various dblk sizes and offsets can be determined by examining
the file sizes on files in the `dblk/` directory:
- byte        number of bytes written to the dblk file
- .recnum     number of records in dblk file
- .last_rec   offset of last record of dblk file
- .last_sync  offset of last SYNC record of dblk file
- note        number of notes written
```
ls -al tags/\<node_id:ffffffffffff\>/tag/sd/0/dblk/
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
hexdump -s 512 -n 512 tags/\<node_id:ffffffffffff\>/tag/sd/0/dblk/byte
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
echo 'this is a test' > tags/\<node_id:ffffffffffff\>/tag/sd/0/dblk/note
```
Check to see how many notes have been written
```
ls -l tags/\<node_id:ffffffffffff\>/tag/sd/0/dblk/note
```
Output looks like this.
```
--w--w---- 1 root root 143 Feb  2 16:13 tags/<node_id:ffffffffffff>/tag/sd/0/dblk/note
```
# Errorcodes
## TagNet Application Errorcodes
## Linux File System Errorcodes

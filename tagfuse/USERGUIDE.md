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
'''
   root
   |-- info
   |   +-- sens
   |       +-- gps
   |           +-- xyz
   |-- poll
   |   |-- cnt
   |   +-- ev
   |-- sd
   |   +-- 0
   |       |-- dblk
   |       |   |-- 0
   |       |   |-- 1
   |       |   +-- note
   |       +-- img
   +-- sys
       |-- active
       |-- backup
       |-- golden
       |-- nib
       +-- running
'''


# coding: utf-8

# # Si446x Device Direct Access TagNet Software Image Load

# In[1]:

get_ipython().system(u'pwd')
get_ipython().magic(u'autosave 0')
import sys
sys.path.append("../si446x/si446x")
get_ipython().magic(u"run '../si446x/si446x/notebooks/si446x_Device_Layer.ipynb'")


# In[ ]:

import sys
sys.path.append("../tagnet/tagnet")
from tagmessages import TagMessage, TagPoll, TagGet, TagPut, TagHead
from tagnames import TagName
from tagtlv import TagTlv, TagTlvList, tlv_types


# In[ ]:

import datetime
print('Test Start Time: {}'.format(datetime.datetime.now()))
print('Si446x Radio Device Driver Version: {}'.format(si446x_device_version()))


# ##  Start up Radio

# In[ ]:

radio = si446x_device_start_radio()


# In[ ]:

si446x_device_show_config(radio.dump_radio())


# ## Check for Command Error

# In[ ]:

status = radio.get_chip_status()
if (status.chip_pend.CMD_ERROR):
    print(status)


# ##  Configure Radio

# In[ ]:

config = si446x_device_config_radio(radio)

si446x_device_show_config(radio.dump_radio())
total = 0
print('\n=== const config strings:')
for s in config:
    print((hexlify(s)))
    total += len(s) - 4
print('\n total: {}'.format(total))


# ## Transfer Software Image using TagNet

# In[3]:

from __future__ import print_function
from builtins import *                  # python3 types
from time import sleep
from datetime import datetime
#from struct import unpack, pack, Struct
import struct as pystruct
from binascii import hexlify
import os.path


# ### Image Info description
# Image Description Information stored in the Image File

# In[5]:

filename    = '/tmp/test.bin'

C structures from TAG code define image info metadata

typedef struct {                        /* little endian order  */
  uint16_t build;                       /* that's native for us */
  uint8_t  minor;
  uint8_t  major;
} image_ver_t;

typedef struct {
  uint8_t  hw_rev;
  uint8_t  hw_model;
} hw_ver_t;

typedef struct {
  uint32_t    sig;                      /* must be IMAGE_INFO_SIG to be valid */
  uint32_t    image_start;              /* where this binary loads            */
  uint32_t    image_length;             /* byte length of entire image        */
  uint32_t    vector_chk;               /* simple checksum over vector table  */
  uint32_t    image_chk;                /* simple checksum over entire image  */
  image_ver_t ver_id;
  hw_ver_t    hw_ver;
} image_info_t;
# In[6]:

#  IMAGE_INFO provides information about a Tag software image. This data is
#  embedded in the image itself. The IMAGE_META_OFFSET is the offset into
#  the image where image_info lives in the image.  It directly follows the
#  exception vectors which are 0x140 bytes long.
# 
#  This struct will have to change, If MSP432 vector table length changes.
# 
IMAGE_INFO_SIG = 0x33275401
IMAGE_META_OFFSET = 0x140
IMAGE_INFO_DEFAULT = [IMAGE_INFO_SIG, 0x20000, (0x140*2)+0x1c, 0, 0, 257, 1, 1, 0xde, 2]
#
# Struct created for accessing image info (little indian)
# sig, image_start, imagelength, vector_chk, image_chk, im_build, im_minor, im_major, im_rev, im_model = image_info
#
IM_FIELDS = '<LLLLLHBBBB'
image_info_struct = pystruct.Struct(IM_FIELDS)
IMAGE_MIN_SIZE  =  (IMAGE_META_OFFSET + image_info_struct.size)


# In[7]:

# write out simple default binary input file for testing purposes
#
if not os.path.isfile(filename):
    with open(filename,'wb') as outfile:
        buf = bytearray(IMAGE_META_OFFSET)
        for x in range(1,IMAGE_META_OFFSET): buf[x] = x & 0x7f
        outfile.write(buf)
        outfile.write(bytearray(image_info_struct.pack(*IMAGE_INFO_DEFAULT)))
        outfile.write(buf)


# ### utility routines for handling image load

# In[8]:

# debug flags
PRINT_MAX = 40


# In[9]:

# default paramters
MAX_WAIT            = 20
MAX_RECV            = 255
MAX_PAYLOAD         = 254

RADIO_POWER         = 1
SHORT_DELAY         = .1


# In[10]:

# build Image PUT Request
def im_send_request(fd, write_max, vers, eof=False):
    # base image name
    req_name = TagName ('/tag/sd')                 + TagTlv(tlv_types.NODE_ID, -1)                 + TagTlv(0)                 + TagTlv('img')                 + TagTlv(tlv_types.VERSION, vers)

    # optionally add offset to name
    if (fd.tell() > 0):
        req_name += TagTlv(tlv_types.OFFSET, fd.tell())

    # build the PUT mesage object
    req_obj = TagPut(req_name)

    # optionally add payload
    if eof:
        # send end of file indication
        pload = [TagTlv(tlv_types.EOF)]
    elif (fd.tell() < write_max):
        # determine payload to send
        max_write = 254 - req_obj.pkt_len()
        if ((file_size - fd.tell()) < max_write):
                max_write = file_size - fd.tell()
        pload = bytearray(f.read(max_write))
    # else
        # just send without payload
    
    # print out details of request
    print("REQUEST MSG")
    print(req_obj.header)
    print(req_obj.name)
    if (pload is not None):
        req_obj.payload = pload
    req_msg = req.build()
    print("   req len: {},  payload len: {}".format(len(req_msg), len(load)))
    print("   ", hexlify(req_msg[:PRINT_MAX]),"...", hexlify(req_msg[-PRINT_MAX:]))
    
    # send request msg
    si446x_device_send_msg(radio, im_req_buf, RADIO_POWER)
    xcnt += 1
    return req_obj, req_msg


# In[11]:

def im_get_response():
    rmsg_buf, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, MAX_WAIT)
    if (not rmsg_buf):
        return None
    rsp_obj = rsp_msg.parse()
    # get offset
    offset = -1
    if (rsp_obj.payload)             and (rsp_obj.payload[0].tlv_type() == tlv_types.OFFSET)             and (rsp_obj.payload[0].value() == fd.tell()):
        offset = rsp_obj.payload[0].value()

    # print out details of response
    print("REQUEST MSG")
    print(rsp_obj.header)
    print(rsp_obj.name)
    if (rsp_obj.payload):
        print("   offset: {}, req len: {},  payload len: {}".format(len(rsp_msg), len(load)))
        print("   ", hexlify(rsp_msg[:PRINT_MAX]),"...", hexlify(rsp_msg[-PRINT_MAX:]))
    return rsp_obj, rsp_msg, offset


# ### main funtion for transfer of image to tag

# In[22]:

xcnt        = 0
rcnt        = 0
rssi        = 0
            
radio.trace._enable()

prp         = bytearray(1)
prp[0] = 0x22
radio.set_property('MODEM', 0x4c, prp) 
prp[0] = 40
radio.set_property('PKT', 0x0b, prp)      # set tx fifo threshhold

start = datetime.now()
print(start)

class LoadException(Exception):
    pass

try:
    # open input file and determine its length
    infile = open(filename, 'rb')
    infile.seek(0, 2) # seek to the end
    file_size = infile.tell()
    if file_size < IMAGE_MIN_SIZE: raise LoadException("input file too short")
    infile.seek(0)    # seek to the beginnnig

    # get image info from input file and sanity check
    infile.seek(IMAGE_META_OFFSET) # seek to location of image info
    image_info = image_info_struct.unpack(infile.read(image_info_struct.size))
    print("file information")
    pstr = "  signature: {}, start: {}, length: {}, vector_chk: {}, image_chk: {}"
    print(pstr.format(sig, im_start, im_length, vec_chk, im_chk))
    pstr = "  version: ({}, {}, {}), rev: {}, model: {}"
    print(pstr.format(im_major, im_minor, im_build, im_rev, im_model))
    sig, im_start, im_length, vec_chk, im_chk, im_build, im_minor, im_major, im_rev, im_model = image_info
    if sig != IMAGE_INFO_SIG: raise LoadException("image metadata is invalid")
    infile.seek(0)    # seek to the beginnnig

    # loop to transfer image data to tag
    offset = 0
    while (file_size - infile.tell() > 0):
        print("\n>>>> file size, offset: ", file_size, infile.tell())
        im_send_request(infile, filesize, (im_major, im_rev, im_model))
        rsp_obj, rsp_msg, offset = im_get_response()
        # check that offset is expected
        if offset != infile.tell():
            raise LoadException("bad offset, got {}, expected {}".format(rsp_obj.payload[0].value(), infile.tell()))
        sleep(SHORT_DELAY)

    # send end of file to complete the image load
    im_send_request(infile, filesize, (im_major, im_rev, im_model), True)
    rsp_obj, rsp_msg, offset = im_get_response()

finally:
    infile.close()

except LoadException, reason:
    print("load exception", reason)

except IOError, e:
    print("i/o error", e)

print('\ndone')


# ## Get Directory

# In[ ]:

image_manager_name = TagName ('/tag/sd')                 + TagTlv(tlv_types.NODE_ID, -1)                 + TagTlv(0)                 + TagTlv('img') dir_info = TagGet(image_manager_name)
print(dir_info.name)
dir_msg = dir_info.build()
print(len(dir_msg),hexlify(dir_msg))


# In[ ]:

l = si446x_device_send_msg(radio, dir_msg, pwr)
dir_msg, rssi, status = si446x_device_receive_msg(radio, MAX_RECV, MAX_WAIT)
if (dir_msg):
    dir_obj = TagMessage(dir_msg)
    print("DIRECTORY LISTING")
    print(dir_obj.header)
    print(obj_obj.name)
    print(obj_obj.payload)


# ## Get Chip Status

# In[ ]:

print(radio.get_chip_status())


# ## Interactive Group Properties

# In[ ]:

interact(si446x_device_group_fetch_and_decode, group=radio_config_group_ids.encoding)


# ## Interactive  Command Status Responses

# In[ ]:

interact(si446x_device_command_fetch_and_decode, cmd=radio_status_cmd_ids.encoding)


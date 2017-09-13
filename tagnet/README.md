TagNet
======

Dan Maltbie <dmaltbie@daloma.org>
v1.0, July 2016

*License*: [MIT](http://www.opensource.org/licenses/mit-license.php)

Introduction
------------

The TagNet protocol stack is designed to operate in the constraint-bound
environment of the MM6A Tag. The primary usage of the protocol is for
control, configuration, tracking, and data collection over a wireless
low-power adhoc radio network. The radio is a major consumer of power
requiring the protocol must take care to limit wasted transmission time.
The mobility of the Tag requires the protocol to handle the intermittent
and potentially brief transmission with as much information as possible.

This protocol does not depend on the heavy protocol stacks typically found
in IoT types of networks. But these networks suffer many flaws when
operating in the harsh untethered world of Tags. Instead it operates
with a simple, clean, and efficient protocol based on named data networks
proposed over 10 years ago by Van Jacobson. He observed that the TCP/IP
networks that work so well for the wired world we live in will not
operate at the scale of massive mobile device deployments such as IoT.

Because of the power and radio performance constraints, this
implementation of named data networking simpilfies and compacts the
radio packet structure. As such, it is not interoperable with NDN or CCN.
For TagNe, each packet, or message, consists of a fixed header portion
followed by the name of the data object, followed by any associated data,
or payload. A packet may be a request or a response and it also indicates
an action to perform (e.g., GET or PUT).

Except for the fixed header which has pre-defined fields, values in other
structures are specified using Type-Length-Value (TLV) strings. The type
field describes the value, such as integer, string, or UTC time. The
length field specifies the length of the value string. The value field
contains the value of the typed datum.

The name found in the message is constructed from a series of TLVs
concatenated into the fully qualified identification. Thus names behave
like a file name, in that they can be constructed in any arbitrary form.

The payload can be constructed from a list of TLVs or may be a raw block
of data (as determined by a flag in the fixed header).

See <document from mindmap> for more details

The application programming interface uses the following classes:

TagTlv            typed data object
TagTlvList        list of TLVs, such as used in a name or payload
TagName           name of the data object, (a TagTlvList)
TagMessage        packet formatted message with name and payload

Types of TLVs

    STRING        string of bytes
    INTEGER       integer of any size
    GPS           GPS 3D coordinates
    TIME          UTC time (full)
    NODE_ID       Unique node identifier
    NODE_NAME     nickname assigned to node
    OFFSET        partial record access
    SEQUENCE      index for random record access
    COUNT         max number of records to return
    EOF           end of file (last record)
    VERSION       version information (xx.yy.zz)


Directory Content
-----------------

- tagtlv.py       contains TagTlv and TagTlvList classes
                           tlv_types
- tagnames.py     contains TagName class
- tagmessages.py  contains TagMessage, TagPayload, TagPoll, TagBeacon,
                           TagGet, TagPut, and TagResponse classes

Usage Example
-------------

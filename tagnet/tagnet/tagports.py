from twisted.internet import reactor, defer

from txdbus import client, error

from construct import *

from si446x.tagmaster import tagnet_dbus_interface

# in the future the tagnet dbus interface will be separated from tagmaster. It will be
# moved to a standalone switch module. For now, tagmaster directly supports the interface
# and will control exchange of packets with the radio network.


BUS_NAME = 'org.tagnet.tagnet'
OBJECT_PATH = '/org/tagnet/tagmaster'   # object name includes device id/port numbers

si446x_dbus_interface = DBusInterface( BUS_NAME,
                            Method('send', arguments='s', returns='s'),
                            Signal('receive', 'ayu'),
                         )

# class TagNetDbus - driver is controlled by this dbus interface
#
class TagNetDbus (objects.DBusObject):
    dbusInterfaces = [tagnet_dbus_interface]
    
    def __init__(self, objectPath):
        super(TagNetDbus, self).__init__(self, objectPath)
#        objects.DBusObject.__init__(self, objectPath)
        self.obj_handler = objects.DBusObjectHandler(self)

        #----  DBus Interface Methods  ----

    def dbus_send(self, s):
        return 'ok ' + s

        #----  DBus Interface Signals  ----

    def signal_receive(self):
        self.emitSignal('receive', 'abc')

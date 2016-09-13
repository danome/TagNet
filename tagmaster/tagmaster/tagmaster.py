#!/usr/bin/env python

import time
import sys
import signal
import binascii
import signal

from twisted.internet      import reactor, defer
from txdbus                import client, error, objects
from txdbus.interface      import DBusInterface, Method, Signal
from twisted.python        import log

from construct             import *

from tagnet                import TagName, TagMessage, TagPayload, TagPoll

log.startLogging(sys.stdout)

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

msg_header_s = Struct('msg_header_s',
                    Byte('length'),
                    Byte('sequence'),
                    UBInt16('address'),
                    Enum(Byte('test_mode'),
                         DISABLED = 0,
                         RUN  = 1,
                         PEND = 2,
                         PING = 3,
                         PONG = 4,
                         REP  = 5,
                         )
                    )

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# global list of tag devoces that are currently within radio range
#
taglist = dict()

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

TAGNET_BUS_NAME = 'org.tagnet.tagmaster'           # bus name for tagnet forwarder
TAGNET_OBJECT_PATH = '/org/tagnet/tagmaster'

tagmaster_dbus_interface = DBusInterface(TAGNET_BUS_NAME,
                                      Method('tag_list', arguments='s', returns='ay' ),
                                      Signal('tag_found', 'ay' ),  # report new tag
                                      Signal('tag_lost', 'ay' ),   # report tag out of range
                                      Signal('tag_events', 'ay' ), # report new tag events
                                      Signal('tagnet_status', 'ay' ),
                                      )

class TagNetDbus(objects.DBusObject):
    """
    provides the interface for accessing the tagnet port
    """
    dbusInterfaces = [tagmaster_dbus_interface]
                 
    def __init__(self, object_path):
        super(TagNetDbus, self).__init__(object_path)
        self.object_path = object_path
        self.obj_handler = objects.DBusObjectHandler(self)
        log.msg('TagNetDbus-init, {}'.format(self.object_path))

    def dbus_tag_list(self, arg):
        log.msg('TagNetDbus-tag_list: {}'.format(arg))
        return bytearray('You sent {}'.format(arg))

    def signal_tagnet_status(self):
        self.emitSignal('tagnet_status', bytearray('ok'))

    def signal_tag_lost(self):
        self.emitSignal('tag_lost', bytearray('ok'))

    def signal_tag_found(self):
        self.emitSignal('tag_found', bytearray('ok'))

    def signal_tag_events(self):
        self.emitSignal('tag_events', bytearray('ok'))

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

class TagNetComponent(object):
    def __init__(self, conn):
        self.conn = conn
        super(TagNetComponent, self).__init__()
        log.msg('TagNetComponent-init, {}'.format(self.conn))

    def start(self, conn):
        self.conn = conn
        log.msg('TagNetComponent-start, {}'.format(self.conn))
        try:
            self.conn.exportObject(TagNetDbus(TAGNET_OBJECT_PATH))
            deferred = self.conn.requestBusName(TAGNET_BUS_NAME)
            deferred.addCallback(self.dbus_ready)
        except error.DBusException, e:
            log.msg('TagNetComponent-start-error, {}'.format(e))

    def dbus_ready(self, bus_id):
        self.bus_id = bus_id
        log.msg('TagNetComponent-bus_ready: {}, {}'.format(TAGNET_BUS_NAME, self.bus_id))
        
    def on_error(self, failure):
        log.msg('TagNetComponent-error: {}'.format(str(failure)))

    def report_changes(self, changes):
        log.msg('TagNetComponent-report_changes, {}'.format(changes))
        pass
        
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

from si446x import si446x_dbus_interface

SI446X_BUS_NAME = 'org.tagnet.si446x'           # bus name for si446x device driver
SI446X_OBJECT_PATH = '/org/tagnet/si446x/0/0'   # object name includes device id/port numbers

POLL_DELAY = 5   # seconds

class Si446xComponent(object):
    def __init__(self, conn, report_changes):
        self.conn = conn
        self.report_changes = report_changes
        self.poll_count = 0
        self.recv_count = 0
        self.last_t = None
        self.msg = bytearray(('\x00' * msg_header_s.sizeof()) + 'hello world')
        self.msg[0] = len(self.msg)-1
        self.pwr = 32
        self.last_t = None
        self.this_t = None
        super(Si446xComponent, self).__init__()

    def start(self, conn):
        log.msg('get remote si446x object:  {}  {}'.format(SI446X_BUS_NAME, SI446X_OBJECT_PATH))
        deferred = conn.getRemoteObject(SI446X_BUS_NAME,
                                        SI446X_OBJECT_PATH,
                                        interfaces=si446x_dbus_interface)
        deferred.addCallback(self.got_remote)

    def got_remote(self, robj):
        log.msg('got remote si446x object {}  {}'.format(SI446X_BUS_NAME, SI446X_OBJECT_PATH))
        self.robj = robj
        robj.notifyOnSignal('receive', self.on_receive)
#        robj.notifyOnSignal('receive', self.on_receive, interface=si446x_dbus_interface)
#        robj.onError(self.on_error)
        reactor.callLater(0, self.send_poll, robj)

    def send_poll(self, robj):
        log.msg('send_poll')
        msg = TagPoll().build()
        log.msg(binascii.hexlify(msg))
        deferred =  robj.callRemote('send', msg, self.pwr)
        deferred.addCallback(self.poll_sent)
        log.msg('sent packet (p:{} r:{})'.format(self.poll_count, self.recv_count))

    def poll_sent(self, e):
        log.msg('poll_sent')
        self.poll_count += 1
        reactor.callLater(POLL_DELAY, self.send_poll, self.robj)

    def on_error(self, failure):
        log.msg(str(failure))

    def on_receive(self, msg, rssi):
        log.msg('on_receive')
        changes = []
        self.report_changes(changes)
        self.this_t = time.time()
        self.last_t = self.last_t if (self.last_t) else time.time()
        self.last_t = self.this_t

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def reactor_loop():
    """
    controls the main processing loop using reactor.run()
    """
    def on_running():
        """
        called when the twisted reactor is running
        """
        log.msg('reactor_loop Starting')
        try:
            conn = client.connect(reactor)
            tagnet_do = TagNetComponent(conn)
            conn.addCallback(tagnet_do.start)
            conn.addErrback(tagnet_do.on_error)
            conn = client.connect(reactor)
            si446x_do = Si446xComponent(conn, tagnet_do.report_changes)
            conn.addCallback(si446x_do.start)
            conn.addErrback(si446x_do.on_error)
        except error.DBusException, e:
            log.msg('reactor_loop Setup Error: {}'.format(e))
            reactor.stop()

    signal.signal(signal.SIGINT, SIGINT_CustomEventHandler)
    signal.signal(signal.SIGHUP, SIGINT_CustomEventHandler)
    reactor.callWhenRunning(on_running)
    reactor.run()

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def SIGINT_CustomEventHandler(num, frame):
    k={1:"SIGHUP", 2:"SIGINT"}
    log.msg("Recieved signal - " + k[num])
    if frame is not None:
        log.msg("SIGINT at %s:%s"%(frame.f_code.co_name, frame.f_lineno))
    log.msg("In SIGINT_CustomEventHandler")
    if num == 2:
        log.msg("shutting down ....")
        reactor.stop()
     
if __name__ == '__main__':
    reactor_loop()

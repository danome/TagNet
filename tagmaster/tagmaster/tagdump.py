#!/usr/bin/env python
from __future__ import print_function   # python3 print function
from builtins import *

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
from si446x                import si446xtrace, si446xdef

log.startLogging(sys.stdout)

from si446x import si446x_dbus_interface

SI446X_BUS_NAME = 'org.tagnet.si446x'           # bus name for si446x device driver
SI446X_OBJECT_PATH = '/org/tagnet/si446x/0/0'   # object name includes device id/port numbers

POLL_DELAY = 5   # seconds

class Si446xComponent(object):
    def __init__(self, conn, report_changes=None):
        self.conn = conn
        self.report_changes = report_changes
        self.send_count = 0
        self.recv_count = 0
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
        robj.notifyOnSignal('new_status', self.on_status_change)
#        robj.notifyOnSignal('receive', self.on_receive, interface=si446x_dbus_interface)
#        robj.onError(self.on_error)
        reactor.callLater(0, self.get_dump, robj)

    def get_dump(self, robj):
        log.msg('get_dump')
        deferred =  robj.callRemote('dump_trace', '', 0, '', '', 0)
        deferred.addCallback(self.got_dump)
        log.msg('sent packet (p:{} r:{})'.format(self.send_count, self.recv_count))
        self.send_count += 1

    def got_dump(self, arg):
        log.msg('got_dump')
        for a in arg:
            print(type(a), len(a), a)
        reactor.callLater(POLL_DELAY, self.get_dump, self.robj)
        self.recv_count += 1

    def on_error(self, failure):
        log.msg(str(failure))

    def on_status_change(self, msg, rssi):
        log.msg('on_receive')
        changes = []
        self.report_changes(changes)
        self.this_t = time.time()
        self.last_t = self.last_t if (self.last_t) else time.time()
        self.last_t = self.this_t
#end class

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
            si446x_do = Si446xComponent(conn)
            conn.addCallback(si446x_do.start)
            conn.addErrback(si446x_do.on_error)
        except error.DBusException, e:
            log.msg('reactor_loop Setup Error: {}'.format(e))
            reactor.stop()

    signal.signal(signal.SIGINT, SIGINT_CustomEventHandler)
    signal.signal(signal.SIGHUP, SIGINT_CustomEventHandler)
    reactor.callWhenRunning(on_running)
    reactor.run()
#end def

def SIGINT_CustomEventHandler(num, frame):
    k={1:"SIGHUP", 2:"SIGINT"}
    log.msg("Recieved signal - " + k[num])
    if frame is not None:
        log.msg("SIGINT at %s:%s"%(frame.f_code.co_name, frame.f_lineno))
    log.msg("In SIGINT_CustomEventHandler")
    if num == 2:
        log.msg("shutting down ....")
        reactor.stop()
#end def

if __name__ == '__main__':
    reactor_loop()

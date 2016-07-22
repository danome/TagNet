#!/usr/bin/env python

import time

from twisted.internet import reactor, defer

from txdbus           import client, error
from txdbus.interface import DBusInterface, Signal

from si446x.si446xdvr import si446x_dbus_interface

count = 0
robj = None
last_t=0

#@defer.inlineCallbacks
def onReceiveSignal( msg, pwr ):
    global robj, count, last_t
    last_t = last_t if (last_t) else time.time()
    this_t = time.time()
    print '({:^20.6f} {:.6f})Got {} ({}): {}, {}'.format(this_t, this_t-last_t,
                                                 len(msg), count, msg[:16], pwr)
    last_t = this_t
#    e = yield robj.callRemote('send', msg, pwr)
#    print 'respond ({}) {}'.format(count, e)
    count += 1

@defer.inlineCallbacks
def main():
    global robj, count
    try:
        cli   = yield client.connect(reactor)

        robj  = yield cli.getRemoteObject('org.tagnet.si446x',
                                          '/org/tagnet/si446x/0/0',
                                          si446x_dbus_interface )
        print 'got remote object'
        robj.notifyOnSignal( 'receive', onReceiveSignal )
    except error.DBusException, e:
        print 'DBus Error:', e

reactor.callWhenRunning(main)
reactor.run()


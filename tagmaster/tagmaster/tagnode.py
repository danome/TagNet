#!/usr/bin/env python

import signal
import sys

from binascii             import hexlify

from twisted.internet     import reactor, defer
from txdbus               import client, error
from twisted.python       import log

from construct            import *

from tagnet               import TagPayload, TagResponse, TagMessage

log.startLogging(sys.stdout)

from si446x.si446xdvr     import si446x_dbus_interface

SI446X_BUS_NAME = 'org.tagnet.si446x'           # bus name for si446x device driver
SI446X_OBJECT_PATH = '/org/tagnet/si446x/0/0'   # object name includes device id/port numbers

pwr = 32
send_count = 0
recv_count = 0
robj = None

#@defer.inlineCallbacks
def on_receive(rxbuf, rssi):
    global send_count, recv_count
    recv_count += 1
    log.msg('got {}:{}, {}'.format(len(rxbuf), rssi, hexlify(bytearray(rxbuf))))
    rsp = TagResponse(TagMessage(bytearray(rxbuf)))
#    e = yield robj.callRemote('send', rsp.build(), pwr)
    e=0
    log.msg('send packet s:{} r:{} e:{}, {}'.format(send_count, recv_count, e, hexlify(rsp.build())))
    send_count += 1

@defer.inlineCallbacks
def on_running():
    global robj
    try:
        cli = yield client.connect(reactor)
        robj = yield cli.getRemoteObject(SI446X_BUS_NAME,
                                         SI446X_OBJECT_PATH,
                                         si446x_dbus_interface)
        log.msg('got remote object')
        robj.notifyOnSignal( 'receive', on_receive )
    except error.DBusException, e:
        log.msg('send Failed. org.example is not available')

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

def reactor_loop():
    reactor.callWhenRunning(on_running)
    reactor.run()

if __name__ == '__main__':
    reactor_loop()

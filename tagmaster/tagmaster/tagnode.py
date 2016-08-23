from twisted.internet import reactor, defer

from txdbus import client, error

from construct import *

from si446x.si446xdvr import si446x_dbus_interface

from tagnet import TagPayload, TagResponse, TagMessage

pwr = 32
send_count = 0
recv_count = 0
robj = None

@defer.inlineCallbacks
def on_receive(rxbuf, pwr):
    global send_count
    recv_count += 1
    print 'got {}: {}'.format(len(rxbuf), pwr)
    rsp = TagResponse(rxbuf)
    e = yield robj.callRemote('send', rsp.build(), pwr)
    print 'send packet ({}:{}) {}'.format(send_count, recv_count, e)
    send_count += 1

@defer.inlineCallbacks
def on_running():
    global robj
    try:
        cli = yield client.connect(reactor)
        robj = yield cli.getRemoteObject( 'org.tagnet.si446x',
                                       '/org/tagnet/si446x/0/0',
                                       si446x_dbus_interface)
        print 'got remote object'
        robj.notifyOnSignal( 'receive', on_receive )
    except error.DBusException, e:
        print 'send Failed. org.example is not available'

def reactor_loop():
    reactor.callWhenRunning(on_running)
    reactor.run()

if __name__ == '__main__':
    reactor_loop()

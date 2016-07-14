from twisted.internet import reactor, defer

from txdbus import client, error

from construct import *

from si446x.si446xdvr import si446x_dbus_interface

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

msg = bytearray(('\x00' * msg_header_s.sizeof()) + 'hello world')
pwr = 32

@defer.inlineCallbacks
def send_again(robj):
    e = yield robj.callRemote('send', msg, pwr)
    print 'send packet', e
    reactor.callLater(2, send_again, robj)

@defer.inlineCallbacks
def main():

    try:
        cli = yield client.connect(reactor)

        robj = yield cli.getRemoteObject( 'org.tagnet.si446x',
                                       '/org/tagnet/si446x/0/0',
                                       si446x_dbus_interface)
        print 'got remote object'
        reactor.callLater(1, send_again, robj)

    except error.DBusException, e:
        print 'send Failed. org.example is not available'

#    reactor.stop()


msg[0] = len(msg)-1

reactor.callWhenRunning(main)
reactor.run()


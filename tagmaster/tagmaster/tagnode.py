from twisted.internet import reactor, defer

from txdbus import client, error

from si446x.si446xdvr import si446x_dbus_interface


@defer.inlineCallbacks
def send_again(robj):
    e = yield robj.callRemote('send', [3,2,1,0], 32)
    print 'sent packet', e
    reactor.callLater(1, send_again, robj)

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

reactor.callWhenRunning(main)
reactor.run()


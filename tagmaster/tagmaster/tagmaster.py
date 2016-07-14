#!/usr/bin/env python

#!/usr/bin/env python

from twisted.internet import reactor, defer

from txdbus           import client, error
from txdbus.interface import DBusInterface, Signal

from si446x.si446xdvr import si446x_dbus_interface


def onReceiveSignal( tickCount ):
    print 'Got tick signal: ', tickCount

@defer.inlineCallbacks
def main():

    try:
        cli   = yield client.connect(reactor)

        robj  = yield cli.getRemoteObject('org.tagnet.si446x',
                                          '/org/tagnet/si446x/0/0',
                                          si446x_dbus_interface )

        robj.notifyOnSignal( 'send', onReceiveSignal )

    except error.DBusException, e:
        print 'DBus Error:', e


reactor.callWhenRunning(main)
reactor.run()

#@@@@@@@

from twisted.internet import reactor
from txdbus import client

            
def on_receive( a, u ):
    print 'Got receive signal: ',a,u 

def onErr(err):
    print 'Error: ', err.getErrorMessage()



d = client.connect(reactor, 'session')

d.addCallback( lambda cli: cli.getRemoteObject( 'org.tagnet.si446x', '/org/tagnet/si446x/0/0' ) )
d.addCallback( lambda ro: ro.notifyOnSignal( 'receive', on_receive ) ) 
d.addErrback( onErr )

reactor.run()

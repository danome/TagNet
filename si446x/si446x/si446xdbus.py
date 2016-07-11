#!/usr/bin/env python

from twisted.internet import reactor

from txdbus import client, objects
from txdbus.interface import DBusInterface, Method, Signal

BUS_NAME = 'org.tagnet.si446x'
OBJECT_PATH = '/org/tagenet/si446x/0/0'   # object name includes device id/port numbers

class Si446xDbus (objects.DBusObject):

    iface = DBusInterface( 'org.tagnet.si446x',
                           Method('Control', arguments='s', returns='s'),
                           Method('Send', arguments='su', returns='s'),
                           Method('CCA', returns='s'),
                           Signal('Receive', 'su'),
                           Signal('Status', 's'),
                         )

    dbusInterfaces = [iface]

    def __init__(self, objectPath):
        objects.DBusObject.__init__(self, objectPath)
        self.uuid = binascii.hexlify(os.urandom(16))
        self.status = 'OFF'
        self.obj_handler = objects.DBusObjectHandler(self)
        #self.obj_handler.exportObject(self)

    def set_fsm(self, fsm):
        self.fsm = fsm

    def interrupt_cb(self, channel):
        si446xdvr.interrupt_handler(self.fsm, self.radio)

    def timeout_cb(self):
        self.fsm.receive(Events.E_WAIT_DONE)

    def sendStatus(self):
        self.emitSignal('Status', self.status)

    def start_timer(self, delay): # seconds (float)
        reactor.callLater(delay, self.timeout_cb)

    ### DBus Interface


#### MAIN Initialization

def onErr(err):
    print 'Failed: ', err.getErrorMessage()
    reactor.stop()

def onConnected(conn):
    dbus = Si446xDbus(OBJECT_PATH)
    radio = Si446xRadio(0, dbus.interrupt_cb)
    fsm = constructFiniteStateMachine(
        inputs=Events,
        outputs=Actions,
        states=States,
        table=table,
        initial=States.S_SDN,
        richInputs=[],
        inputContext={},
        world=MethodSuffixOutputer(FsmActionHandlers(radio, dbus)),
    )
    dbus.set_fsm(fsm)
    conn.exportObject(MyObj(OBJECT_PATH))
    dn = conn.requestBusName(BUS_NAME)

    def onReady(_):
        s = 'Starting up Si446x radio driver. Bus name: {}, Object Path: {}'
        print s.format(BUS_NAME, OBJECT_PATH)
#        signal driver state
        #fsm.receive(Events.E_TURNON)

    dn.addCallback(onReady)
    return dn

if __name__ == '__main__':
    dc = client.connect(reactor)
    dc.addCallback(onConnected)
    dc.addErrback(onErr)
    reactor.run()

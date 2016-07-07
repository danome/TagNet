#
#
from __future__ import print_function
from time import sleep

from twisted.python.constants import Names, NamedConstant
from twisted.internet import reactor

from txdbus import client, objects
from txdbus.interface import DBusInterface, Method, Signal

from machinist import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

from construct import *

from si446xFSM import Events, Actions, States, table
from si446xact import FsmActionHandlers
from si446xradio import Si446xRadio
from si446xdef import *

BUS_NAME = 'org.tagnet.si446x'
OBJECT_PATH = '/org/tagenet/si446x/0/0'   # object name includes device id/port numbers

# class Si446xDbus - driver is controlled by this dbus interface
#
class Si446xDbus (objects.DBusObject):
    iface = DBusInterface( 'org.tagnet.si446x',
                           Method('control', arguments='s', returns='s'),
                           Method('send', arguments='su', returns='s'),
                           Method('cca', returns='s'),
                           Signal('receive', 'su'),
                           Signal('status', 's'),
                         )
    dbusInterfaces = [iface]
    self.control_action = None

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

    def async_interrupt(self, channel):
        reactor.callfromthread(self.interrupt_cb, self, channel)

    def config_cb(self):
        fsm_step(self.fsm, self.radio, Events.E_CONFIG_DONE)

    def config_done(self):
        reactor.callLater(0, self.config_cb)

    def timeout_cb(self):
        fsm_step(self.fsm, self.radio, Events.E_WAIT_DONE)

    def start_timer(self, delay): # seconds (float)
        reactor.callLater(delay, self.timeout_cb)

    ### DBus Interface

    def dbus_control(self, action):
        if (self.control_action):
            return 'error'
        self.control_action = action
        if (action is 'TURNON'):
            fsm_step(self.fsm, self.radio, Events.E_TURNON)
        else if (action is 'TURNOFF'):
            fsm_step(self.fsm, self.radio, Events.E_TURNOFF)
        else if (action is 'STANDBY'):
            fsm_step(self.fsm, self.radio, Events.E_STANDBY)
        else:
            return 'error'
        return 'ok'

    def dbus_send(self, buf, power):
        if (self.fsm.state is not States.S_RX_ON):
            return 'error'
        self.radio.tx.buf = buf
        self.radio.tx.power = power
        fsm_step(self.fsm, self.radio, Events.E_TRANSMIT)
        return 'ok'
    
    def dbus_cca(self):
        return self.radio.rx.rssi
    
    def signal_receive(self, buf, rssi):
        self.emitSignal('receive', buf, rssi)
    
    def signal_status(self):
        self.control_action = None
        self.emitSignal('status', self.status)
    
    
def process_interrupts(fsm, radio, pend):
#    pend = fast_frr_rsp_s.parse(frr)
    clr_flags = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    got_ints = False
    #print(fsm.state, (fsm.state is States.S_RX_ON), pend)
    if ((pend.modem_pend.INVALID_SYNC_PEND) and (fsm.state is States.S_RX_ON)):
        step_fsm(fsm, radio, Events.E_INVALID_SYNC)
        clr_flags.modem_pend.INVALID_SYNC_PEND_CLR = False
        got_ints = True
    if ((pend.modem_pend.PREAMBLE_DETECT_PEND) and (fsm.state is States.S_RX_ON)):
        step_fsm(fsm, radio, Events.E_PREAMBLE_DETECT)
        clr_flags.modem_pend.PREAMBLE_DETECT_PEND_CLR = False
        got_ints = True
    if ((pend.modem_pend.SYNC_DETECT_PEND) and (fsm.state is States.S_RX_ON)):
        step_fsm(fsm, radio, Events.E_SYNC_DETECT)
        clr_flags.modem_pend.SYNC_DETECT_PEND_CLR = False
        got_ints = True
    if ((pend.ph_pend.CRC_ERROR_PEND) and (fsm.state is States.S_RX_ACTIVE)):
        step_fsm(fsm, radio, Events.E_CRC_ERROR)
        clr_flags.ph_pend.CRC_ERROR_PEND_CLR = False
        got_ints = True
    if ((pend.ph_pend.PACKET_RX_PEND) and (fsm.state is States.S_RX_ACTIVE)):
        step_fsm(fsm, radio, Events.E_PACKET_RX)
        clr_flags.ph_pend.PACKET_RX_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.PACKET_SENT_PEND):
        step_fsm(fsm, radio, Events.E_PACKET_SENT)
        clr_flags.ph_pend.PACKET_SENT_PEND_CLR = False
        got_ints = True
    if ((pend.ph_pend.RX_FIFO_ALMOST_FULL_PEND) and (fsm.state is States.S_RX_ACTIVE)):
        step_fsm(fsm, radio, Events.E_RX_THRESH)
        clr_flags.ph_pend.RX_FIFO_ALMOST_FULL_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND):
        step_fsm(fsm, radio, Events.E_TX_THRESH)
        clr_flags.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND_CLR = False
        got_ints = True
#    radio.clear_interrupts(clr_flags)
    #print(got_ints)
    if (got_ints):
        return clr_flags
    else:
        None

# interrupt_handler - process interrupts until no more exist
#
def interrupt_handler(fsm, radio):
    j = 5
    pending_ints = radio.get_interrupts()
    while (True):
        #print(radio.fast_all().encode('hex'), "d-int", fsm.state)
        clr_flags = process_interrupts(\fsm, radio, pending_ints)
        if (not clr_flags):
            break
        pending_ints = radio.get_clear_interrupts(clr_flags)
        #print('ints',radio.fast_all().encode('hex'))
        j -= 1
        if (j <= 0):
            radio.clear_interrupts()  #something seems stuck
            break


        def call_back(channel):
    global flag
    flag = True
    #print('driver: Edge detected on channel %s'%channel)
    #print('-')

def step_fsm(fsm, radio, ev):
    fsm.receive(ev)
    #print(radio.fast_all().encode('hex'), 'step', fsm.state, ev)

def test_cycle():
    global flag
    flag = False
    radio = Si446xRadio(0, call_back)
    si446xDriver = constructFiniteStateMachine(
        inputs=Events,
        outputs=Actions,
        states=States,
        table=table,
        initial=States.S_SDN,
        richInputs=[],
        inputContext={},
        world=MethodSuffixOutputer(FsmActionHandlers(radio)),
    )
    step_fsm(si446xDriver, radio, Events.E_TURNON)
    step_fsm(si446xDriver, radio, Events.E_WAIT_DONE)
    step_fsm(si446xDriver, radio, Events.E_WAIT_DONE)
    step_fsm(si446xDriver, radio, Events.E_CONFIG_DONE)
    for i in range(20000):
        #print(radio.get_interrupts())
        if (flag):
            #flag=False
            interrupt_handler()
        sleep(.001)
        #if ((i % 100) == 0): print(radio.fast_all().encode('hex'), 'driver')
    step_fsm(si446xDriver, radio, Events.E_TURNOFF)


# MAIN Initialization

def onErr(err):
    print 'Failed: ', err.getErrorMessage()
    reactor.stop()

def onConnected(conn):
    dbus = Si446xDbus(OBJECT_PATH)
    radio = Si446xRadio(0, dbus.async_interrupt)
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
    conn.exportObject(dbus)
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

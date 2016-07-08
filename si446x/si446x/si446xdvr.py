#!/usr/bin/env python
#
#
from __future__ import print_function
from time import sleep
import binascii
import os

from twisted.python.constants import Names, NamedConstant
from twisted.internet import reactor

from txdbus import client, objects
from txdbus.interface import DBusInterface, Method, Signal

from machinist import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

from construct import *

from si446xFSM import Events, Actions, States, table
from si446xact import Si446xFsmActionHandlers
from si446xradio import Si446xRadio
from si446xdef import *

BUS_NAME = 'org.tagnet.si446x'
OBJECT_PATH = '/org/tagnet/si446x/0/0'   # object name includes device id/port numbers

# class Si446xDbus - driver is controlled by this dbus interface
#
class Si446xDbus (objects.DBusObject):
    iface = DBusInterface( 'org.tagnet.si446x',
                           Method('control', arguments='s', returns='s'),
                           Method('send', arguments='su', returns='s'),
                           Method('cca', returns='u'),
                           Signal('receive', 'su'),
                           Signal('status', 's'),
                           Signal('send_cmp', 's'),
                         )
    dbusInterfaces = [iface]
    
    def __init__(self, objectPath):
        objects.DBusObject.__init__(self, objectPath)
        self.uuid = binascii.hexlify(os.urandom(16))
        self.status = 'OFF'
        self.control_event = None
        self.obj_handler = objects.DBusObjectHandler(self)

    def marry(self, fsm, radio):
        self.fsm = fsm
        self.radio = radio

    ### DBus Interface Handlers

    def dbus_control(self, action):
        print('action', action)
        if (self.control_event):
            return 'dbus_control busy {}'.format(self.control_event)
        if (action == 'TURNON'):
            if ((self.fsm['machine'].state != States.S_SDN) and
                (self.fsm['machine'].state != States.S_STANDBY)):
                return 'ealready'
            self.control_event = Events.E_TURNON
        elif (action == 'TURNOFF'):
            if (self.fsm['machine'].state == States.S_SDN):
                return 'ealready'
            self.control_event = Events.E_TURNOFF
        elif (action == 'STANDBY'):
            if (self.fsm['machine'].state == States.S_STANDBY):
                return 'ealready'
            self.control_event = Events.E_STANDBY
        else:
            return 'dbus_control error {}'.format(action)
        step_fsm(self.fsm, self.radio, self.control_event)
        return 'ok {}'.format(self.fsm['machine'].state)

    def dbus_send(self, buf, power):
        if (self.fsm['actions'].tx['buffer']):
            return 'busy'
        if (self.fsm['machine'].state is not States.S_RX_ON):
            return 'error {}'.format(self.fsm['machine'].state)
        self.fsm['actions'].tx['buffer'] = buf
        self.fsm['actions'].tx['power'] = power
        step_fsm(self.fsm, self.radio, Events.E_TRANSMIT)
        return 'ok'
    
    def dbus_cca(self):
        return self.fsm['actions'].rx['rssi']
    
    def signal_receive(self):
        self.emitSignal('receive', self.fsm['actions'].rx['buffer'], self.fsm['actions'].rx['rssi'])
        self.fsm['actions'].rx['buffer'] = None
    
    def signal_status(self):
        if (self.fsm['machine'].state is States.S_SDN):
            self.status = 'OFF'
        elif (fsm['machine'].state is States.S_STANDBY):
            self.status = 'STANDBY'
        else:
            self.status = 'ON'
        self.emitSignal('status', self.status)
        self.control_event = None

    def signal_send_cmp(self, condition):
        self.emitSignal('send_cmp', condition)
        self.fsm['actions'].tx['buffer'] = None
    
    ### Asynchronous Event Handlers
    
    def interrupt_cb(self, channel):
        interrupt_handler(self.fsm['machine'], self.radio)

    def async_interrupt(self, channel):
        reactor.callfromthread(self.interrupt_cb, self, channel)

    def config_cb(self):
        step_fsm(self.fsm, self.radio, Events.E_CONFIG_DONE)

    def config_done(self):
        reactor.callLater(0, self.config_cb)

    def timeout_cb(self):
        step_fsm(self.fsm, self.radio, Events.E_WAIT_DONE)

    def start_timer(self, delay): # seconds (float)
        return reactor.callLater(delay, self.timeout_cb)


# process_interrupts - for each interrupt source process the fsm event transition
#
# return list of cleared pending flags, or None if no flags cleared
# note that logic seems backwards, a zero (false) means to clear the pending flag
#
def process_interrupts(fsm, radio, pend):
    clr_flags = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    got_ints = False
    if ((pend.modem_pend.INVALID_SYNC_PEND) and (fsm['machine'].state is States.S_RX_ON)):
        step_fsm(fsm, radio, Events.E_INVALID_SYNC)
        clr_flags.modem_pend.INVALID_SYNC_PEND_CLR = False
        got_ints = True
    if ((pend.modem_pend.PREAMBLE_DETECT_PEND) and (fsm['machine'].state is States.S_RX_ON)):
        step_fsm(fsm, radio, Events.E_PREAMBLE_DETECT)
        clr_flags.modem_pend.PREAMBLE_DETECT_PEND_CLR = False
        got_ints = True
    if ((pend.modem_pend.SYNC_DETECT_PEND) and (fsm['machine'].state is States.S_RX_ON)):
        step_fsm(fsm, radio, Events.E_SYNC_DETECT)
        clr_flags.modem_pend.SYNC_DETECT_PEND_CLR = False
        got_ints = True
    if ((pend.ph_pend.CRC_ERROR_PEND) and (fsm['machine'].state is States.S_RX_ACTIVE)):
        step_fsm(fsm, radio, Events.E_CRC_ERROR)
        clr_flags.ph_pend.CRC_ERROR_PEND_CLR = False
        got_ints = True
    if ((pend.ph_pend.PACKET_RX_PEND) and (fsm['machine'].state is States.S_RX_ACTIVE)):
        step_fsm(fsm, radio, Events.E_PACKET_RX)
        clr_flags.ph_pend.PACKET_RX_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.PACKET_SENT_PEND):
        step_fsm(fsm, radio, Events.E_PACKET_SENT)
        clr_flags.ph_pend.PACKET_SENT_PEND_CLR = False
        got_ints = True
    if ((pend.ph_pend.RX_FIFO_ALMOST_FULL_PEND) and (fsm['machine'].state is States.S_RX_ACTIVE)):
        step_fsm(fsm, radio, Events.E_RX_THRESH)
        clr_flags.ph_pend.RX_FIFO_ALMOST_FULL_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND):
        step_fsm(fsm, radio, Events.E_TX_THRESH)
        clr_flags.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND_CLR = False
        got_ints = True
    if (got_ints):
        return clr_flags
    else:
        None


# interrupt_handler - process interrupts until no more exist
#
# get interrupts from radio device and process until nothing is pending
#
def interrupt_handler(fsm, radio):
    pending_ints = radio.get_interrupts()
    for n in range(5):
        #print(radio.fast_all().encode('hex'), "d-int", fsm['machine'].state)
        clr_flags = process_interrupts(fsm, radio, pending_ints)
        if (not clr_flags):
            return
        pending_ints = radio.get_clear_interrupts(clr_flags)
        #print('ints',radio.fast_all().encode('hex'))
    # got here if something seems stuck, clear all interrupts
    radio.clear_interrupts()


# step_fsm - invoke event driven state transition and corresponding action
#
# Use this routine rather than calling fsm.receive() is so that timing
# and trace event information can be logged
#
def step_fsm(fsm, radio, ev):
    fsm['machine'].receive(ev)
    #print(radio.fast_all().encode('hex'), 'step', fsm['machine'].state, ev)


# MAIN Initialization
#
def onConnected(conn):
    dbus = Si446xDbus(OBJECT_PATH)
    radio = Si446xRadio(0, dbus.async_interrupt)
    actions = Si446xFsmActionHandlers(radio, dbus)
    machine = constructFiniteStateMachine(
        inputs=Events,
        outputs=Actions,
        states=States,
        table=table,
        initial=States.S_SDN,
        richInputs=[],
        inputContext={},
        world=MethodSuffixOutputer(actions),
    )
    fsm={'actions': actions, 'machine': machine}
    dbus.marry(fsm, radio)
    conn.exportObject(dbus)
    dn = conn.requestBusName(BUS_NAME)

    def onReady(_):
        s = ' Si446x radio driver [ {}, {} ] is ready for business'
        print(s.format(BUS_NAME, OBJECT_PATH))
        dbus.signal_status()

    dn.addCallback(onReady)
    return dn

def onErr(err):
    print('Failed: ', err.getErrorMessage())
    reactor.stop()

def reactor_loop():
    dc = client.connect(reactor)
    dc.addCallback(onConnected)
    dc.addErrback(onErr)
    reactor.run()

if __name__ == '__main__':
    reactor_loop()


### extra
#
def cycle():
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



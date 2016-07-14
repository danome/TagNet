#!/usr/bin/env python
#
#
from __future__ import print_function
from time import sleep
import binascii
import os
import platform

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
import si446xtrace

BUS_NAME = 'org.tagnet.si446x'
OBJECT_PATH = '/org/tagnet/si446x/0/0'   # object name includes device id/port numbers

si446x_dbus_interface = DBusInterface( 'org.tagnet.si446x',
                           Method('control', arguments='s', returns='s'),
                           Method('send', arguments='ayu', returns='s'),
                           Method('status', returns='s'),
                           Method('dump_trace', arguments='sudsu', returns='s'),
                           Method('clear_status', returns='s'),
                           Method('cca', returns='u'),
                           Signal('receive', 'ayu'),
                           Signal('new_status', 's'),
                           Signal('send_cmp', 's'),
                         )

# class Si446xDbus - driver is controlled by this dbus interface
#
class Si446xDbus (objects.DBusObject):
    dbusInterfaces = [si446x_dbus_interface]
    
    def __init__(self, objectPath, trace=None):
        objects.DBusObject.__init__(self, objectPath)
        self.uuid = binascii.hexlify(os.urandom(16))
        self.status = 'OFF'
        self.control_event = None
        self.obj_handler = objects.DBusObjectHandler(self)
        self.trace = trace if (trace) else si446xtrace.Trace(100)

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
            self.fsm['actions'].tx['buffer'] = None
            self.fsm['actions'].rx['buffer'] = None
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
            return 'busy {}'.format(self.fsm['machine'].state)
        if (self.fsm['machine'].state is not States.S_RX_ON):
            return 'error {}'.format(self.fsm['machine'].state)
        self.fsm['actions'].tx['buffer'] = buf
        self.fsm['actions'].tx['power'] = power
        step_fsm(self.fsm, self.radio, Events.E_TRANSMIT)
        return 'ok'
    
    def dbus_cca(self):
        return self.fsm['actions'].rx['rssi']
    
    def dbus_status(self):
        s = '[{}] {}, {}, unshuts {}'.format(
            platform.node(),
            self.status,
            self.fsm['machine'].state,
            self.fsm['actions'].ioc['unshuts'],)
        s += '\nRX: '
        for r in ['packets','len_errors','timeouts','sync_errors','crc_errors','rssi']:
            s += '{} {}, '.format(r, self.fsm['actions'].rx[r])
        s += '\nTX: '
        for r in ['packets','errors','timeouts','power']:
            s += '{} {}, '.format(r, self.fsm['actions'].tx[r])
        return s

    def dbus_dump_trace(self, f, n, t, m, s):
        self.trace.display(filter=f, count=n, begin=t, mark=m, span=s)
        return 'ok'
    
    def dbus_clear_status(self):
        self.fsm['actions'].ioc['unshuts'] = 0
        s =  self.dbus_status()
        for r in [ 'packets', 'len_errors', 'timeouts', 'sync_errors','crc_errors']:
            self.fsm['actions'].rx[r] = 0
        for r in [ 'packets', 'errors', 'timeouts']:
            self.fsm['actions'].tx[r] = 0
        return s

    def signal_receive(self):
        r = self.fsm['actions'].rx['buffer']
        self.emitSignal('receive', bytearray(r), int(self.fsm['actions'].rx['rssi']))
        self.fsm['actions'].rx['buffer'] = None
    
    def signal_new_status(self):
        if (self.fsm['machine'].state == States.S_SDN):
            self.status = 'OFF'
        elif (self.fsm['machine'].state == States.S_STANDBY):
            self.status = 'STANDBY'
        else:
            self.status = 'ON'
        s = '{}, {}'.format(self.status, self.fsm['machine'].state)
        print ('new_status',s)
        self.emitSignal('new_status', s)
        self.control_event = None

    def signal_send_cmp(self, condition):
        self.emitSignal('send_cmp', condition)
        self.fsm['actions'].tx['buffer'] = None
    
    ### Asynchronous Event Handlers
    
    def interrupt_cb(self, channel):
        self.trace.add('RADIO_INT', 'sync')
        interrupt_handler(self.fsm, self.radio)

    def async_interrupt(self, channel):
        self.trace.add('RADIO_INT', 'async')
        reactor.callFromThread(self.interrupt_cb, channel)

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
    pending_ints = radio.get_clear_interrupts()
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
    s = '{} / {} frr:{}'.format(ev.name,
                  fsm['machine'].state.name,
                  radio.fast_all().encode('hex'))
    fsm['trace'].add('RADIO_FSM', s)
    fsm['machine'].receive(ev)
    #print(radio.fast_all().encode('hex'), 'step', fsm['machine'].state, ev)


# MAIN Initialization
#
def onConnected(conn):
    trace =  si446xtrace.Trace(10000)
    dbus = Si446xDbus(OBJECT_PATH, trace=trace)
    radio = Si446xRadio(device=0, callback=dbus.async_interrupt, trace=trace)
    print('init radio done')
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
    fsm={'actions': actions, 'machine': machine, 'trace': trace}
    dbus.marry(fsm, radio)
    conn.exportObject(dbus)
    dn = conn.requestBusName(BUS_NAME)

    def onReady(_):
        s = ' Si446x radio driver [ {}, {} ] is ready for business'
        print(s.format(BUS_NAME, OBJECT_PATH))
        dbus.signal_new_status()

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
    trace =  si446xtrace.Trace(100)
    dbus = Si446xDbus(OBJECT_PATH, trace=trace)
    radio = Si446xRadio(device=0, callback=dbus.async_interrupt, trace=trace)
    print('init radio done')
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
    fsm={'actions': actions, 'machine': machine, 'trace': trace}
    dbus.marry(fsm, radio)

    step_fsm(fsm, radio, Events.E_TURNON)
    step_fsm(fsm, radio, Events.E_WAIT_DONE)
    step_fsm(fsm, radio, Events.E_WAIT_DONE)
    step_fsm(fsm, radio, Events.E_CONFIG_DONE)
    trace.display()
    for i in range(20000):
        interrupt_handler(fsm, radio)
        sleep(.001)
        if ((i % 1000) == 0): trace.display(count=10)
    step_fsm(fsm, radio, Events.E_TURNOFF)



#!/usr/bin/env python
#
#
from __future__ import print_function
from builtins import *

import os
import signal
import platform
from time import sleep, time
import binascii

from twisted.python.constants import Names, NamedConstant
from twisted.internet         import reactor
from twisted.python           import log

from txdbus                   import client, objects
from txdbus.interface         import DBusInterface, Method, Signal

from machinist                import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

from construct                import *

from si446xFSM                import Events, Actions, States, table
from si446xact                import Si446xFsmActionHandlers
from si446xradio              import Si446xRadio
from si446xdef                import *
import si446xtrace

__all__ = ['BUS_NAME', 'OBJECT_PATH', 'si446x_dbus_interface', 'Si446xDbus', 'reactor_loop']

BUS_NAME = 'org.tagnet.si446x'
OBJECT_PATH = '/org/tagnet/si446x/0/0'   # object name includes device id/port numbers

si446x_dbus_interface = DBusInterface( BUS_NAME,
                            Method('cca', returns='u'),
                            Method('clear_status', returns='s'),
                            Method('control', arguments='s', returns='s'),
                            Method('dump_radio', arguments='s', returns='s'),
                            Method('dump_trace', arguments='sissu', returns='a(dyssay)'),
                            Method('send', arguments='ayu', returns='s'),
                            Method('spi_send', arguments='ays', returns='s'),
                            Method('spi_send_recv', arguments='ayuss', returns='ay'),
                            Method('status', returns='s'),
                            Signal('new_status', 's'),
                            Signal('receive', 'ayu'),
                            Signal('send_cmp', 's'),
                         )

class Si446xDbus(objects.DBusObject):
    """
    provides the interface for accessing the SI446x Radio Chip Driver
    """
    dbusInterfaces = [si446x_dbus_interface]
    
    def __init__(self, objectPath, trace=None):
        super(Si446xDbus,self).__init__(objectPath)
        self.uuid = binascii.hexlify(os.urandom(16))
        self.status = 'OFF'
        self.control_event = None
        self.obj_handler = objects.DBusObjectHandler(self)
        self.trace = trace if (trace) else si446xtrace.Trace(100)

    def marry(self, fsm, radio):
        self.fsm = fsm
        self.radio = radio

    ### DBus Interface Methods

    def dbus_cca(self):
        return self.fsm['actions'].rx['rssi']
    
    def dbus_clear_status(self):
        self.fsm['actions'].ioc['unshuts'] = 0
        s =  self.dbus_status()
        for r in [ 'packets', 'len_errors', 'timeouts', 'sync_errors','crc_errors']:
            self.fsm['actions'].rx[r] = 0
        for r in [ 'packets', 'errors', 'timeouts']:
            self.fsm['actions'].tx[r] = 0
        return s + self.radio.trace.format_time(time())

    def dbus_control(self, action):
        self.radio.trace.add('RADIO_IOC', action)
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
        if (self.control_event):
            step_fsm(self.fsm, self.radio, self.control_event)
            self.control_event =  None
            return 'ok {} {}:{}'.format(self.radio.trace.format_time(time()),
                                         self.fsm['machine'].state, self.control_event)
        return 'user control {} failed {}'.format(action, self.radio.trace.format_time(time()))

    def dbus_dump_radio(self, s):
        if (s == 'REFRESH'):
            self.radio.dump_radio()
        self.radio.read_silicon_info()
        self.radio.spi.read_frr(0,4)
        self.radio.get_interrupts()
        self.radio.get_gpio()
        self.radio.trace_radio()
        return 'ok ' + self.radio.trace.format_time(time())
    
    def dbus_dump_trace(self, f, n, t, m, s):
        return self.trace.rb.get()
    
    def dbus_send(self, buf, power):
        if (self.fsm['actions'].tx['buffer']):
            return 'busy {}'.format(self.fsm['machine'].state)
        if (self.fsm['machine'].state is not States.S_RX_ON):
            return 'error {}'.format(self.fsm['machine'].state)
        self.fsm['actions'].tx['buffer'] = buf
        self.fsm['actions'].tx['power'] = power
        self.fsm['actions'].tx['offset'] = 0
        step_fsm(self.fsm, self.radio, Events.E_TRANSMIT)
        return 'ok ' + self.radio.trace.format_time(time())
    
    def dbus_spi_send(self, pkt, form):
        self.radio.spi.command(pkt, form)
        return 'ok ' + self.radio.trace.format_time(time())

    def dbus_spi_send_recv(self, pkt, rlen, c_form, r_form):
        self.radio.spi.command(pkt, c_form)
        return bytearray(self.radio.spi.response(rlen, r_form)[0:rlen])

    def dbus_status(self):
        s = '[{}] {}, {}, unshuts {}'.format(
            platform.node(),
            self.status,
            self.fsm['machine'].state,
            self.fsm['actions'].ioc['unshuts'],)
        s += '\n RX: '
        for r in ['packets','len_errors','timeouts','sync_errors','crc_errors','rssi']:
            s += '{} {}, '.format(r, self.fsm['actions'].rx[r])
        s += '\n TX: '
        for r in ['packets','errors','timeouts','power']:
            s += '{} {}, '.format(r, self.fsm['actions'].tx[r])
        return s + self.radio.trace.format_time(time())

    ### DBus Signals
    
    def signal_new_status(self):
        if (self.fsm['machine'].state == States.S_SDN):
            self.status = 'OFF'
        elif (self.fsm['machine'].state == States.S_STANDBY):
            self.status = 'STANDBY'
        else:
            self.status = 'ON'
        s = '{}, {} {}'.format(self.status, self.fsm['machine'].state,
                                 self.radio.trace.format_time(time()))
        print ('new_status',s)
        self.emitSignal('new_status', s)
        self.control_event = None

    def signal_receive(self):
        r = self.fsm['actions'].rx['buffer']
        self.emitSignal('receive', bytearray(r), int(self.fsm['actions'].rx['rssi']))
        self.fsm['actions'].rx['buffer'] = None
    
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
#end class

def process_interrupts(fsm, radio, pend):
    """
    process_interrupts - for each interrupt source process the event transition

    return list of cleared pending flags, or None if no flags cleared
    note that logic seems backwards, but a zero (false) means to clear the 
    pending flag (set to one if you don't want to clear the flag)
    """
    clr_flags = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    got_ints = False
    if (pend.modem_pend.INVALID_SYNC_PEND):
        if (fsm['machine'].state is States.S_RX_ON):
            step_fsm(fsm, radio, Events.E_INVALID_SYNC)
        else:
            radio.trace.add('RADIO_ERROR', 'Phantom INVALID_SYNC_PEND')
        clr_flags.modem_pend.INVALID_SYNC_PEND_CLR = False
        got_ints = True
    if (pend.modem_pend.PREAMBLE_DETECT_PEND):
        if (fsm['machine'].state is States.S_RX_ON):
            step_fsm(fsm, radio, Events.E_PREAMBLE_DETECT)
        else:
            radio.trace.add('RADIO_ERROR', 'Phantom PREAMBLE_DETECT_PEND')
        clr_flags.modem_pend.PREAMBLE_DETECT_PEND_CLR = False
        got_ints = True
    if (pend.modem_pend.SYNC_DETECT_PEND):
        if (fsm['machine'].state is States.S_RX_ON):
            step_fsm(fsm, radio, Events.E_SYNC_DETECT)
        else:
            radio.trace.add('RADIO_ERROR', 'Phantom SYNC_DETECT_PEND')
        clr_flags.modem_pend.SYNC_DETECT_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.CRC_ERROR_PEND):
        if (fsm['machine'].state is States.S_RX_ACTIVE):
            step_fsm(fsm, radio, Events.E_CRC_ERROR)
        else:
            radio.trace.add('RADIO_ERROR', 'Phantom CRC_ERROR_PEND')
        clr_flags.ph_pend.CRC_ERROR_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.PACKET_RX_PEND):
        if (fsm['machine'].state is States.S_RX_ACTIVE):
            step_fsm(fsm, radio, Events.E_PACKET_RX)
        else:
            radio.trace.add('RADIO_ERROR', 'Phantom PACKET_RX_PEND')
        clr_flags.ph_pend.PACKET_RX_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.PACKET_SENT_PEND):
        step_fsm(fsm, radio, Events.E_PACKET_SENT)
        clr_flags.ph_pend.PACKET_SENT_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.RX_FIFO_ALMOST_FULL_PEND):
        if (fsm['machine'].state is States.S_RX_ACTIVE):
            step_fsm(fsm, radio, Events.E_RX_THRESH)
        else:
            radio.trace.add('RADIO_ERROR', 'Phantom RX_FIFO_ALMOST_FULL_PEND')
        clr_flags.ph_pend.RX_FIFO_ALMOST_FULL_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND):
        if (fsm['machine'].state is States.S_TX_ACTIVE):
            step_fsm(fsm, radio, Events.E_TX_THRESH)
        else:
            radio.trace.add('RADIO_ERROR', 'Phantom TX_FIFO_ALMOST_EMPTY_PEND')
        clr_flags.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND_CLR = False
        got_ints = True
    if (pend.modem_pend.RSSI_PEND):
        clr_flags.modem_pend.RSSI_PEND_CLR = False
        got_ints = True
    if (pend.modem_pend.INVALID_PREAMBLE_PEND):
        clr_flags.modem_pend.INVALID_PREAMBLE_PEND_CLR = False
        got_ints = True
    if (got_ints):
        return clr_flags
    else:
        return None
#end def


def interrupt_handler(fsm, radio):
    """
    Process interrupts until no more exist

    Get interrupts from radio device and process until nothing is pending.
    """
    pending_ints = radio.get_clear_interrupts()
    for n in range(5):
        clr_flags = process_interrupts(fsm, radio, pending_ints)
        if (clr_flags is None):
            return
        radio.trace.add('RADIO_INT', 'clearing interrupts: {}'.format(clr_flags.__repr__()))
        pending_ints = radio.get_clear_interrupts(clr_flags)
    # got here if something seems stuck, clear all interrupts
    radio.trace.add('RADIO_ERROR', 'interrupts stuck: {}'.format(pending_ints.__repr__()))
    radio.get_gpio()


def step_fsm(fsm, radio, ev):
    """
    Invoke event driven state transition and corresponding action

    Use this routine rather than calling fsm.receive() is so that timing
    and trace event information can be logged.
    """
    frr = radio.fast_all()
    s = '{} / {} frr:{}'.format(ev.name,
                  fsm['machine'].state.name,
                                binascii.hexlify(frr))
    fsm['trace'].add('RADIO_FSM', s)
    fsm['machine'].receive(ev)
    #if (frr[1] or frr[2]):
    #    reactor.calllater(0, interrupt_handler, fsm, radio)

def setup_driver():
    """
    Instantiate all of the driver components

    includes the following objects:
    trace, dbus, radio, state machine actions, finite state machine.

    Returns list of [fsm, radio, dbus] object references.
    """
    trace =  si446xtrace.Trace(1000)
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
    return [fsm, radio, dbus]

def start_driver(fsm, radio, dbus):
    """
    Signal current (off) status and turn on driver
    """
    s = ' Si446x radio driver [ {}, {} ] is ready for business'
    print(s.format(BUS_NAME, OBJECT_PATH))
    # transition radio automatically out of off state
    step_fsm(fsm,radio, Events.E_TURNON)
    # signal state change on dbus
    dbus.signal_new_status()

def reactor_loop():
    """
    SI446x Driver reactor loop
    """
    fsm = None
    radio = None
    dbus = None
    def onConnected(conn):
        fsm, radio, dbus = setup_driver()
        conn.exportObject(dbus)
        dn = conn.requestBusName(BUS_NAME)
    
        def onReady(_):
            start_driver(fsm, radio, dbus)

        dn.addCallback(onReady)
        return dn

    def onErr(err):
        print('Failed: ', err.getErrorMessage())
        reactor.stop()

    def SIGINT_CustomEventHandler(num, frame):
        k={1:"SIGHUP", 2:"SIGINT"}
        log.msg("Recieved signal - " + k[num])
        if frame is not None:
            log.msg("SIGINT at %s:%s"%(frame.f_code.co_name, frame.f_lineno))
        log.msg("In SIGINT_CustomEventHandler")
        if num == 2:
            log.msg("shutting down ....")
            if (radio): radio.shutdown()
            reactor.stop()

    signal.signal(signal.SIGINT, SIGINT_CustomEventHandler)
    signal.signal(signal.SIGHUP, SIGINT_CustomEventHandler)
    dc = client.connect(reactor)
    dc.addCallback(onConnected)
    dc.addErrback(onErr)
    reactor.run()

def si446xdvr_test():
    """
    unit test
    """
    fsm, radio, dbus = setup_driver()
    start_driver(fsm, radio, dbus)
    #radio.trace.display()
    import timeit
    sp= "import si446xdvr,si446xFSM,si446xact;fsm, radio, dbus=si446xdvr.setup_driver();a=fsm['actions'];radio.trace._disable()"
    num = 1000
    st="fsm['actions'].output_A_NOP(si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="a.output_A_NOP(si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="si446xact.no_op(fsm['actions'],si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))

    sp= "import si446xdvr,si446xFSM,si446xact;fsm, radio, dbus=si446xdvr.setup_driver();a=fsm['actions'];radio.trace._enable()"
    st="fsm['actions'].output_A_NOP(si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="a.output_A_NOP(si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="si446xact.no_op(fsm['actions'],si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))

    #step_fsm(fsm, radio, Events.E_TURNOFF)
    #interrupt_handler(fsm, radio)
    #sleep(.001)
    #if ((i % 1000) == 0): radio.trace.display(count=-10)

    return [fsm, radio, dbus]


if __name__ == '__main__':
    si446xdvr_test()


#!/usr/bin/env python
#
#
"""
Si446x Radio Driver

This module provides the primary driver interface by provising a DBUS Session
level interface to access driver state machine and radio functions, It also
handles driver initialization,interrupt processing,  state machine control.

The Radio Driver depends on several Python packages for major functions,
including:

- twisted==13.1.0:   Asynchronous I/O event handling framework
                         (see https://twistedmatrix.com/trac/)
- txdbus==1.0.13:    Twisted-based interface to DBUS
                         (see https://github.com/cocagne/txdbus)
- machinist==0.2.0:  Finite State Machine building tool
                         (see https://github.com/ScatterHQ/machinist)
- construct==2.5.5:  Declarative parser for binary structures
                         (see http://construct.readthedocs.io/en/latest/)

The following are important data structures defined/used by the Radio Driver:

- Si446xDbus:        Object inherits from txdbus to define the txdbus interface.
- radio:             Object handling radio hardware operations
- fsm:               Dict containing FSM action and machine objects
- fsm['actions']:    Object containing all FSM-related driver action routines
- fsm['machine']:    Object containing machinist FSM context
- trace:             Object managing the Driver's internal trace buffer

The trace is an in-memory circular array that tracek fine grain driver events,
like state machine changes and radio access functions. Typically the trace
buffer is shared across several modules and is passed as a parameter to object
instantiation. If no trace object is specified, then the object will instantiate
its own trace buffer.

The Driver provides a basic selftest when it is invoked directly as __main__.

Copyright (c) 2016, 2017 Daniel J. Maltbie
"""

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
    Dbus Interface Class for si446x Radio Driver
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
        """
        Associate fsm and radio objects
        """
        self.fsm = fsm
        self.radio = radio

    ### DBus Interface Methods

    def dbus_cca(self):
        """
        Determine if channel is clear to send

        Returns current value of rssi
        """
        return self.fsm['actions'].rx['rssi']

    def dbus_clear_status(self):
        """
        Clear driver status counters
        """
        self.fsm['actions'].ioc['unshuts'] = 0
        s =  self.dbus_status()
        for r in [ 'packets', 'len_errors', 'timeouts', 'sync_errors','crc_errors']:
            self.fsm['actions'].rx[r] = 0
        for r in [ 'packets', 'errors', 'timeouts']:
            self.fsm['actions'].tx[r] = 0
        return self.sign_rsp(s)

    def dbus_control(self, action):
        """
        Control radio operation

        Action string identifiers can be: 'TURNON', 'TURNOFF', and 'STANDBY'
        """
        log.msg("Driver Control: %s"%(action))
        self.radio.trace.add('RADIO_IOC', bytearray(action, 'utf8'))
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
        err = 'user control {} failed {}'.format(action, self.radio.trace.format_time(time()))
        log.msg(err)
        return err

    def dbus_dump_radio(self, s):
        """
        Dump radio settings into the trace buffer

        If 'REFRESH' is specified, then read all settings from radio
        Else just read subset of current status
        """
        if (s == 'REFRESH'):
            self.radio.dump_radio()
        self.radio.read_silicon_info()
        self.radio.spi.read_frr(0,4)
        self.radio.get_interrupts()
        self.radio.get_gpio()
        self.radio.trace_radio()
        return self.sign_rsp('ok')

    def dbus_dump_trace(self, n):
        """
        Return trace records

        If n is zero then return all trace records
        else return most recent 'n' records
        """
        entries =  self.trace.rb.get()
        n = n if (n > 0) else len(entries)
        return entries[len(entries)-n:]

    def dbus_send(self, buf, power):
        """
        Send a Radio packet to the radio

        'buffer' is a bytearray containing the packet to be transmitted
        'power' sets the radio transmit power for this packet
        """
        if (self.fsm['actions'].tx['buffer']):
            return 'busy {}'.format(self.fsm['machine'].state)
        if (self.fsm['machine'].state is not States.S_RX_ON):
            return 'error {}'.format(self.fsm['machine'].state)
        self.fsm['actions'].tx['buffer'] = bytearray(buf)
        self.fsm['actions'].tx['power'] = power
        self.fsm['actions'].tx['offset'] = 0
        print('send: {}, {}'.format(len(self.fsm['actions'].tx['buffer']),
                                    self.fsm['actions'].tx['power']))
        step_fsm(self.fsm, self.radio, Events.E_TRANSMIT)
        return 'ok ' + self.radio.trace.format_time(time())

    def dbus_spi_send(self, pkt, form):
        """
        Send a SPI Command to the radio

        FOR DIAGNOSTIC PURPOSES ONLY
        """
        self.radio.spi.command(pkt, form)
        return 'ok ' + self.radio.trace.format_time(time())

    def dbus_spi_send_recv(self, pkt, rlen, c_form, r_form):
        """
        Send a SPI Command to the radio and read the response

        FOR DIAGNOSTIC PURPOSES ONLY
        """
        self.radio.spi.command(pkt, c_form)
        return bytearray(self.radio.spi.response(rlen, r_form)[0:rlen])

    def dbus_status(self):
        """
        Get current status of radio driver
        """
        s = '{}, {}, unshuts {}'.format(
            self.status,
            self.fsm['machine'].state,
            self.fsm['actions'].ioc['unshuts'],)
        s += '\n RX: '
        for r in ['packets','len_errors','timeouts','sync_errors','crc_errors','rssi']:
            s += '{} {}, '.format(r, self.fsm['actions'].rx[r])
        s += '\n TX: '
        for r in ['packets','errors','timeouts','power']:
            s += '{} {}, '.format(r, self.fsm['actions'].tx[r])
        frr = self.radio.fast_all()
        s += '\n sync frr: {}'.format(binascii.hexlify(frr))
        return self.sign_rsp(s)

    ### DBus Signals

    def signal_new_status(self):
        """
        Issue dbus signal when radio status changes
        """
        if (self.fsm['machine'].state == States.S_SDN):
            self.status = 'OFF'
        elif (self.fsm['machine'].state == States.S_STANDBY):
            self.status = 'STANDBY'
        else:
            self.status = 'ON'
        s = '{}, {} {}'.format(self.status, self.fsm['machine'].state,
                                 self.radio.trace.format_time(time()))
        log.msg('new_status',s)
        self.emitSignal('new_status', s)
        self.control_event = None

    def signal_receive(self):
        """
        Issue dbus signal when radio packet received
        """
        r = self.fsm['actions'].rx['buffer']
        self.emitSignal('receive', bytearray(r), int(self.fsm['actions'].rx['rssi']))
        self.fsm['actions'].rx['buffer'] = None

    def signal_send_cmp(self, condition):
        """
        Issue dbus signal when radio packet send is complete
        """
        self.emitSignal('send_cmp', condition)
        self.fsm['actions'].tx['buffer'] = None

    ### Asynchronous Event Handlers

    def radio_interrupt(self, channel):
        """
        Handle hardware interupt

        This function has been synchronized with twisted thread handler so
        that radio driver state machine re-entrency is controlled and access
        to the radio device is exclusively controlled.

        The interrupt_handler() must clear/process all outstanding interrupt
        sources before returning. Otherwise, we won't get another interrupt
        from the device being blocked by the remaining pending interrupt
        sources.
        """
        frr = self.radio.fast_all()
        self.trace.add('RADIO_INT', 'sync frr: {}'.format(binascii.hexlify(frr)))
#        self.trace.add('RADIO_INT', bytearray(frr), s_name='fast_frr_s')
        interrupt_handler(self.fsm, self.radio)

    def async_interrupt(self, channel):
        """
        Handle external device interrupt

        First, need to synchronize the hardware interrupt event with
        the Twisted thread handler using callFromThread(radio_interrupt).
        Twisted provides a way to defer processing of external events
        until it has reached an appropriate opportunity in its processing
        loop. We use this to synchronize the external interrupt, thus
        ensuring control to critical access resources like the driver
        state machine and radio device registers.

        In this case, the radio_interrupt() funtion is called by the
        main DBus processing loop somtime in the future.
        """
        self.trace.add('RADIO_INT', 'async ch({})'.format(channel))
        reactor.callFromThread(self.radio_interrupt, channel)

    def config_done_sync(self):
        """
        Handle Config_done event

        This function has been synchronized with twisted thread handler so
        that radio driver state machine re-entrency is controlled.
        """
        step_fsm(self.fsm, self.radio, Events.E_CONFIG_DONE)

    def config_done(self):
        """
        Synchronize config completion with twisted thread handler
        """
        reactor.callLater(0, self.config_done_sync)

    def timeout_expired_sync(self):
        """
        Handle radio timer expiration

        This function has been synchronized with twisted thread handler so
        that radio driver state machine re-entrency is controlled.
        """
        step_fsm(self.fsm, self.radio, Events.E_WAIT_DONE)

    def start_timer(self, delay): # seconds (float)
        """
        Start radio timer for delay seconds
        """
        return reactor.callLater(delay, self.timeout_expired_sync)
#end class

def process_interrupts(fsm, radio, pend):
    """
    For each interrupt source process the event transition

    Return list of cleared pending flags, or None if no flags cleared.
    Note that logic seems backwards, but a zero (false) means to clear the
    pending flag (set to one if you don't want to clear the flag) as
    dictated by the Si446x device API.
    """
    clr_flags = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())
    got_ints = False
    if (pend.ph_pend.TX_FIFO_ALMOST_EMPTY):
        step_fsm(fsm, radio, Events.E_TX_THRESH)
        clr_flags.ph_pend.TX_FIFO_ALMOST_EMPTY = False
        got_ints = True
    if (pend.ph_pend.PACKET_SENT):
        step_fsm(fsm, radio, Events.E_PACKET_SENT)
        clr_flags.ph_pend.PACKET_SENT = False
        got_ints = True
    if (pend.ph_pend.RX_FIFO_ALMOST_FULL):
        step_fsm(fsm, radio, Events.E_RX_THRESH)
        clr_flags.ph_pend.RX_FIFO_ALMOST_FULL = False
        got_ints = True
    if (pend.ph_pend.CRC_ERROR):
        step_fsm(fsm, radio, Events.E_CRC_ERROR)
        clr_flags.ph_pend.CRC_ERROR = False
        got_ints = True
    if (pend.ph_pend.PACKET_RX):
        step_fsm(fsm, radio, Events.E_PACKET_RX)
        clr_flags.ph_pend.PACKET_RX = False
        got_ints = True
    if (pend.modem_pend.INVALID_SYNC):
        step_fsm(fsm, radio, Events.E_INVALID_SYNC)
        clr_flags.modem_pend.INVALID_SYNC = False
        got_ints = True
    if (pend.modem_pend.PREAMBLE_DETECT):
        step_fsm(fsm, radio, Events.E_PREAMBLE_DETECT)
        clr_flags.modem_pend.PREAMBLE_DETECT = False
        got_ints = True
    if (pend.modem_pend.SYNC_DETECT):
        step_fsm(fsm, radio, Events.E_SYNC_DETECT)
        clr_flags.modem_pend.SYNC_DETECT = False
        got_ints = True
    if (pend.modem_pend.RSSI):
        clr_flags.modem_pend.RSSI = False
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
    Initially, all pending interrupt sources are retrieved along with
    clearing all sources.
    All pending interrupt sources are processed by process_interrupts(),
    causing the appropriate state machine event to be executed and
    clr_flags to be set to clear the source

    Each time the pending interrupt information is retrieved, interrupts
    that have been serviced will be cleared.

    If after trying to process all outstanding interrupt pending
    sources is not successful, then clear all pending interrupts and
    log the error condition.
    """
    pending_ints = radio.get_clear_interrupts()
    for n in range(5):
        clr_flags = process_interrupts(fsm, radio, pending_ints)
        if (clr_flags is None):
            return
        pending_ints = radio.get_clear_interrupts(clr_flags)
    # got here if something seems stuck, clear all interrupts
    radio.trace.add('RADIO_ERROR', "stuck interrupts")
    radio.get_gpio()   # side effect is to trace current gpio values


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


def setup_driver():
    """
    Instantiate all of the driver components

    includes the following objects:
    trace, dbus, radio, state machine actions, finite state machine

    Returns list of [fsm, radio, dbus] object references
    """
    trace =  si446xtrace.Trace(1000)
    dbus = Si446xDbus(OBJECT_PATH, trace=trace)
    radio = Si446xRadio(device=0, callback=dbus.async_interrupt, trace=trace)
    log.msg('init radio done')
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
    log.msg(s.format(BUS_NAME, OBJECT_PATH))
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
        """
        Handle dbus connection event
        """
        fsm, radio, dbus = setup_driver()
        conn.exportObject(dbus)
        dn = conn.requestBusName(BUS_NAME)

        def onReady(_):
            """
            Handle dbus ready event
            """
            start_driver(fsm, radio, dbus)

        dn.addCallback(onReady)
        return dn

    def onErr(err):
        """
        Handle dbus errors
        """
        log.msg('Failed: ', err.getErrorMessage())
        reactor.stop()

    def SIGINT_CustomEventHandler(num, frame):
        """
        Handle external trap events (SIGHUP, SIGINT)
        """
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
    self test
    """
    fsm, radio, dbus = setup_driver()
    start_driver(fsm, radio, dbus)
    #radio.trace.display()
    import timeit
    sp= "import si446x.si446xdvr,si446x.si446xFSM,si446x.si446xact;fsm, radio, dbus=si446x.si446xdvr.setup_driver();a=fsm['actions'];radio.trace._disable()"
    num = 1000
    print('trace disabled')
    st="fsm['actions'].output_A_NOP(si446x.si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="a.output_A_NOP(si446x.si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="si446x.si446xact.no_op(fsm['actions'],si446x.si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))

    sp= "import si446x.si446xdvr,si446x.si446xFSM,si446x.si446xact;fsm, radio, dbus=si446x.si446xdvr.setup_driver();a=fsm['actions'];radio.trace._enable()"
    print('trace enabled')
    st="fsm['actions'].output_A_NOP(si446x.si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="a.output_A_NOP(si446x.si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="si446x.si446xact.no_op(fsm['actions'],si446x.si446xFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))

    #step_fsm(fsm, radio, Events.E_TURNOFF)
    #interrupt_handler(fsm, radio)
    #sleep(.001)
    #if ((i % 1000) == 0): radio.trace.display(count=-10)

    return [fsm, radio, dbus]


if __name__ == '__main__':
    """
    if this file is invoked directly, then run selftest
    """
    si446xdvr_test()

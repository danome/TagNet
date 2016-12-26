#!/usr/bin/env python
#
#
from __future__ import print_function
from builtins import *

import os
import signal
import platform
from time                     import sleep, time
import binascii

from twisted.python.constants import Names, NamedConstant
from twisted.internet         import reactor
from twisted.python           import log

from txdbus                   import client, objects
from txdbus.interface         import DBusInterface, Method, Signal

from machinist                import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

from construct                import *

from dockcomFSM               import Events, Actions, States, table
from dockcomact               import DockcomFsmActionHandlers
from dockcomserial            import DockcomSerial
from dockcomdef               import *
import dockcomtrace

__all__ = ['BUS_NAME', 'OBJECT_PATH', 'dockcom_dbus_interface', 'DockcomDbus', 'reactor_loop']

BUS_NAME = 'org.tagnet.dockcom'
OBJECT_PATH = '/org/tagnet/dockcom/0/0'   # object name includes device id/port numbers

dockcom_dbus_interface = DBusInterface( BUS_NAME,
                            Method('clear_status', returns='s'),
                            Method('control', arguments='s', returns='s'),
                            Method('dump', arguments='s', returns='s'),
                            Method('dump_trace', arguments='s', returns='a(dyssay)'),
                            Method('send', arguments='ayu', returns='s'),
                            Method('status', returns='s'),
                            Signal('new_status', 's'),
                            Signal('receive', 'ayu'),
                            Signal('send_cmp', 's'),
                         )

class DockcomDbus(objects.DBusObject):
    """
    provides the interface for accessing the Dockcom Serial Chip Driver
    """
    dbusInterfaces = [dockcom_dbus_interface]
    
    def __init__(self, objectPath, trace=None):
        super(DockcomDbus,self).__init__(objectPath)
        self.uuid = binascii.hexlify(os.urandom(16))
        self.status = 'OFF'
        self.control_event = None
        self.obj_handler = objects.DBusObjectHandler(self)
        self.trace = trace if (trace) else dockcomtrace.Trace(100)

    def marry(self, fsm, serial):
        self.fsm = fsm
        self.serial = serial

    ### DBus Interface Methods

    def dbus_clear_status(self):
        self.fsm['actions'].ioc['unshuts'] = 0
        s =  self.dbus_status()
        for r in [ 'packets', 'len_errors', 'timeouts', 'sync_errors','crc_errors']:
            self.fsm['actions'].rx[r] = 0
        for r in [ 'packets', 'errors', 'timeouts']:
            self.fsm['actions'].tx[r] = 0
        return s + self.serial.trace.format_time(time())

    def dbus_control(self, action):
        self.serial.trace.add('SERIAL_IOC', action)
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
            step_fsm(self.fsm, self.serial, self.control_event)
            self.control_event =  None
            return 'ok {} {}:{}'.format(self.serial.trace.format_time(time()),
                                         self.fsm['machine'].state, self.control_event)
        return 'user control {} failed {}'.format(action, self.serial.trace.format_time(time()))

    def dbus_dump(self, s):
        if (s == 'REFRESH'):
            self.serial.dump_serial()
        self.serial.read_silicon_info()
        self.serial.spi.read_frr(0,4)
        self.serial.get_interrupts()
        self.serial.get_gpio()
        self.serial.trace_serial()
        return 'ok ' + self.serial.trace.format_time(time())
    
    def dbus_dump_trace(self, s):
        return self.trace.rb.get()
    
    def dbus_send(self, buf, power):
        if (self.fsm['actions'].tx['buffer']):
            return 'busy {}'.format(self.fsm['machine'].state)
        if (self.fsm['machine'].state is not States.S_RX_ON):
            return 'error {}'.format(self.fsm['machine'].state)
        self.fsm['actions'].tx['buffer'] = buf
        self.fsm['actions'].tx['power'] = power
        self.fsm['actions'].tx['offset'] = 0
        step_fsm(self.fsm, self.serial, Events.E_TRANSMIT)
        return 'ok ' + self.serial.trace.format_time(time())

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
        return s + self.serial.trace.format_time(time())

    ### DBus Signals
    
    def signal_new_status(self):
        if (self.fsm['machine'].state == States.S_SDN):
            self.status = 'OFF'
        elif (self.fsm['machine'].state == States.S_STANDBY):
            self.status = 'STANDBY'
        else:
            self.status = 'ON'
        s = '{}, {} {}'.format(self.status, self.fsm['machine'].state,
                                 self.serial.trace.format_time(time()))
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
        self.trace.add('SERIAL_INT', 'sync')
        interrupt_handler(self.fsm, self.serial)

    def async_interrupt(self, channel):
        self.trace.add('SERIAL_INT', 'async')
        reactor.callFromThread(self.interrupt_cb, channel)

    def config_cb(self):
        step_fsm(self.fsm, self.serial, Events.E_CONFIG_DONE)

    def config_done(self):
        reactor.callLater(0, self.config_cb)

    def timeout_cb(self):
        step_fsm(self.fsm, self.serial, Events.E_WAIT_DONE)

    def start_timer(self, delay): # seconds (float)
        return reactor.callLater(delay, self.timeout_cb)
#end class

def process_interrupts(fsm, serial, pend):
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
            step_fsm(fsm, serial, Events.E_INVALID_SYNC)
        else:
            serial.trace.add('SERIAL_ERROR', 'Phantom INVALID_SYNC_PEND')
        clr_flags.modem_pend.INVALID_SYNC_PEND_CLR = False
        got_ints = True
    if (pend.modem_pend.PREAMBLE_DETECT_PEND):
        if (fsm['machine'].state is States.S_RX_ON):
            step_fsm(fsm, serial, Events.E_PREAMBLE_DETECT)
        else:
            serial.trace.add('SERIAL_ERROR', 'Phantom PREAMBLE_DETECT_PEND')
        clr_flags.modem_pend.PREAMBLE_DETECT_PEND_CLR = False
        got_ints = True
    if (pend.modem_pend.SYNC_DETECT_PEND):
        if (fsm['machine'].state is States.S_RX_ON):
            step_fsm(fsm, serial, Events.E_SYNC_DETECT)
        else:
            serial.trace.add('SERIAL_ERROR', 'Phantom SYNC_DETECT_PEND')
        clr_flags.modem_pend.SYNC_DETECT_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.CRC_ERROR_PEND):
        if (fsm['machine'].state is States.S_RX_ACTIVE):
            step_fsm(fsm, serial, Events.E_CRC_ERROR)
        else:
            serial.trace.add('SERIAL_ERROR', 'Phantom CRC_ERROR_PEND')
        clr_flags.ph_pend.CRC_ERROR_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.PACKET_RX_PEND):
        if (fsm['machine'].state is States.S_RX_ACTIVE):
            step_fsm(fsm, serial, Events.E_PACKET_RX)
        else:
            serial.trace.add('SERIAL_ERROR', 'Phantom PACKET_RX_PEND')
        clr_flags.ph_pend.PACKET_RX_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.PACKET_SENT_PEND):
        step_fsm(fsm, serial, Events.E_PACKET_SENT)
        clr_flags.ph_pend.PACKET_SENT_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.RX_FIFO_ALMOST_FULL_PEND):
        if (fsm['machine'].state is States.S_RX_ACTIVE):
            step_fsm(fsm, serial, Events.E_RX_THRESH)
        else:
            serial.trace.add('SERIAL_ERROR', 'Phantom RX_FIFO_ALMOST_FULL_PEND')
        clr_flags.ph_pend.RX_FIFO_ALMOST_FULL_PEND_CLR = False
        got_ints = True
    if (pend.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND):
        if (fsm['machine'].state is States.S_TX_ACTIVE):
            step_fsm(fsm, serial, Events.E_TX_THRESH)
        else:
            serial.trace.add('SERIAL_ERROR', 'Phantom TX_FIFO_ALMOST_EMPTY_PEND')
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


def interrupt_handler(fsm, serial):
    """
    Process interrupts until no more exist

    Get interrupts from serial device and process until nothing is pending.
    """
    pending_ints = serial.get_clear_interrupts()
    for n in range(5):
        clr_flags = process_interrupts(fsm, serial, pending_ints)
        if (clr_flags is None):
            return
        serial.trace.add('SERIAL_INT', 'clearing interrupts: {}'.format(clr_flags.__repr__()))
        pending_ints = serial.get_clear_interrupts(clr_flags)
    # got here if something seems stuck, clear all interrupts
    serial.trace.add('SERIAL_ERROR', 'interrupts stuck: {}'.format(pending_ints.__repr__()))
    serial.get_gpio()


def step_fsm(fsm, serial, ev):
    """
    Invoke event driven state transition and corresponding action

    Use this routine rather than calling fsm.receive() is so that timing
    and trace event information can be logged.
    """
    frr = serial.fast_all()
    s = '{} / {} frr:{}'.format(ev.name,
                  fsm['machine'].state.name,
                                binascii.hexlify(frr))
    fsm['trace'].add('SERIAL_FSM', s)
    fsm['machine'].receive(ev)
    #if (frr[1] or frr[2]):
    #    reactor.calllater(0, interrupt_handler, fsm, serial)

def setup_driver():
    """
    Instantiate all of the driver components

    includes the following objects:
    trace, dbus, serial, state machine actions, finite state machine.

    Returns list of [fsm, serial, dbus] object references.
    """
    trace =  dockcomtrace.Trace(1000)
    dbus = DockcomDbus(OBJECT_PATH, trace=trace)
    serial = DockcomSerial(device=0, callback=dbus.async_interrupt, trace=trace)
    print('init serial done')
    actions = DockcomFsmActionHandlers(serial, dbus)
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
    dbus.marry(fsm, serial)
    return [fsm, serial, dbus]

def start_driver(fsm, serial, dbus):
    """
    Signal current (off) status and turn on driver
    """
    s = ' Dockcom serial driver [ {}, {} ] is ready for business'
    print(s.format(BUS_NAME, OBJECT_PATH))
    # transition serial automatically out of off state
    step_fsm(fsm,serial, Events.E_TURNON)
    # signal state change on dbus
    dbus.signal_new_status()

def reactor_loop():
    """
    Dockcom Driver reactor loop
    """
    fsm = None
    serial = None
    dbus = None
    def onConnected(conn):
        fsm, serial, dbus = setup_driver()
        conn.exportObject(dbus)
        dn = conn.requestBusName(BUS_NAME)
    
        def onReady(_):
            start_driver(fsm, serial, dbus)

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
            if (serial): serial.shutdown()
            reactor.stop()

    signal.signal(signal.SIGINT, SIGINT_CustomEventHandler)
    signal.signal(signal.SIGHUP, SIGINT_CustomEventHandler)
    dc = client.connect(reactor)
    dc.addCallback(onConnected)
    dc.addErrback(onErr)
    reactor.run()

def dockcomdvr_test():
    """
    unit test
    """
    fsm, serial, dbus = setup_driver()
    start_driver(fsm, serial, dbus)
    #serial.trace.display()
    import timeit
    sp= "import dockcomdvr,dockcomFSM,dockcomact;fsm, serial, dbus=dockcomdvr.setup_driver();a=fsm['actions'];serial.trace._disable()"
    num = 1000
    st="fsm['actions'].output_A_NOP(dockcomFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="a.output_A_NOP(dockcomFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="dockcomact.no_op(fsm['actions'],dockcomFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))

    sp= "import dockcomdvr,dockcomFSM,dockcomact;fsm, serial, dbus=dockcomdvr.setup_driver();a=fsm['actions'];serial.trace._enable()"
    st="fsm['actions'].output_A_NOP(dockcomFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="a.output_A_NOP(dockcomFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))
    st="dockcomact.no_op(fsm['actions'],dockcomFSM.Events.E_0NOP)"
    print('{}:{} {}'.format(timeit.timeit(stmt=st,setup=sp,number=num),num,st))

    #step_fsm(fsm, serial, Events.E_TURNOFF)
    #interrupt_handler(fsm, serial)
    #sleep(.001)
    #if ((i % 1000) == 0): serial.trace.display(count=-10)

    return [fsm, serial, dbus]


if __name__ == '__main__':
    dockcomdvr_test()


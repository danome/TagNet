#
#
from __future__ import print_function
from time import sleep

from twisted.python.constants import Names, NamedConstant

from machinist import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

from si446xFSM import Events, Actions, States, table
from si446xact import FsmActionHandlers
from si446xradio import Si446xRadio

from construct import *
from si446xdef import *



def step_fsm(fsm, radio, ev):
    fsm.receive(ev)
    #print(radio.fast_all().encode('hex'), 'step', fsm.state, ev)
          


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

def call_back(channel):
    global flag
    flag = True
    #print('driver: Edge detected on channel %s'%channel)
    #print('-')


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
    for i in range(2000):
        #print(radio.get_interrupts())
        if (flag):
            #flag=False
            j = 10
            pending_ints = radio.get_interrupts()
            while (True):
                #print(radio.fast_all().encode('hex'), "d-int", si446xDriver.state)
                clr_flags = process_interrupts(si446xDriver, radio, pending_ints)
                if (not clr_flags):
                    break
                pending_ints = radio.get_clear_interrupts(clr_flags)
                #print('ints',radio.fast_all().encode('hex'))
                j -= 1
                if (j <= 0):
                    radio.clear_interrupts()
                    break
        sleep(.01)
        #if ((i % 100) == 0): print(radio.fast_all().encode('hex'), 'driver')
    step_fsm(si446xDriver, radio, Events.E_TURNOFF)
#    si446xDriver.receive(Events.E_WAIT_DONE)


if __name__ == '__main__':
    cycle()

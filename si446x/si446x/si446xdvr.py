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



def step_fsm(fsm, ev):
    fsm.receive(ev)


def process_interrupts(fsm, ints):
    print(ints)
    got_ints = False
    if (ints.modem_pend.INVALID_SYNC_PEND):
        step_fsm(fsm, Events.E_INVALID_SYNC)
        got_ints = True
#    if (ints.modem_pend.INVALID_PREAMBLE_PEND):
#        step_fsm(fsm, Events.E_INVALID_SYNC)
#        got_ints = True
    if (ints.modem_pend.PREAMBLE_DETECT_PEND):
        step_fsm(fsm, Events.E_PREAMBLE_DETECT)
        got_ints = True
    if (ints.modem_pend.SYNC_DETECT_PEND):
        step_fsm(fsm, Events.E_SYNC_DETECT)
        got_ints = True
    if (ints.ph_pend.CRC_ERROR_PEND):
        step_fsm(fsm, Events.E_CRC_ERROR)
        got_ints = True
    if (ints.ph_pend.PACKET_RX_PEND):
        step_fsm(fsm, Events.E_PACKET_RX)
        got_ints = True
    if (ints.ph_pend.PACKET_SENT_PEND):
        step_fsm(fsm, Events.E_PACKET_SENT)
        got_ints = True
    if (ints.ph_pend.RX_FIFO_ALMOST_FULL_PEND):
        step_fsm(fsm, Events.E_RX_THRESH)
        got_ints = True
    if (ints.ph_pend.TX_FIFO_ALMOST_EMPTY_PEND):
        step_fsm(fsm, Events.E_TX_THRESH)
        got_ints = True
    print('got_ints',got_ints)
    return got_ints

def call_back(channel):
    global flag
    flag = True
    print('driver: Edge detected on channel %s'%channel)


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
    step_fsm(si446xDriver, Events.E_TURNON)
    step_fsm(si446xDriver, Events.E_WAIT_DONE)
    step_fsm(si446xDriver, Events.E_WAIT_DONE)
    step_fsm(si446xDriver, Events.E_CONFIG_DONE)
    for i in range(2000):
        #print(radio.get_interrupts())
        if (flag):
            while (process_interrupts(si446xDriver, radio.get_clear_interrupts())):
                pass
            flag=False
        sleep(.01)
    si446xDriver.receive(Events.E_TURNOFF)
#    si446xDriver.receive(Events.E_WAIT_DONE)


if __name__ == '__main__':
    cycle()

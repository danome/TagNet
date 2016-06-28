#
#
from __future__ import print_function

from twisted.python.constants import Names, NamedConstant

from machinist import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

from si446xFSM import Events, Actions, States, table
from si446xact import Si446xActionProcs

class Action_code(object):
    def __init__(self, dev_num):
        self.actions = Si446xActionProcs(dev_num)

    def output_A_CLEAR_SYNC(self, ev):
        print("clear sync")
        self.actions.clear_sync(ev)
    def output_A_CONFIG(self, ev):
        print("config")
        self.actions.config(ev)
    def output_A_NOP (self, ev):
        print("nop")
        self.actions.no_op(ev)
    def output_A_PWR_DN(self, ev):
        print("power down")
        self.actions.pwr_dn(ev)
    def output_A_PWR_UP(self, ev):
        print("power up")
        self.actions.pwr_up(ev)
    def output_A_READY (self, ev):
        print("ready")
        self.actions.ready(ev)
    def output_A_RX_CMP(self, ev):
        print("rx complete")
        self.actions.rx_cmp(ev)
    def output_A_RX_CNT_CRC(self, ev):
        print("rx count crc error")
        self.actions.rx_cnt_crc(ev)
    def output_A_RX_DRAIN_FF(self, ev):
        print("drain rx fifo")
        self.actions.rx_drain_ff(ev)
    def output_A_RX_START(self, ev):
        print("rx start")
        self.actions.rx_start(ev)
    def output_A_RX_TIMEOUT(self, ev):
        print("rx timeout")
        self.actions.rx_timeout(ev)
    def output_A_STANDBY(self, ev):
        print("standby")
        self.actions.standby(ev)
    def output_A_TX_CMP(self, ev):
        print("tx complete")
        self.actions.tx_cmp(ev)
    def output_A_TX_FILL_FF(self, ev):
        print("tx fill fifo")
        self.actions.tx_fill_ff(ev)
    def output_A_TX_START(self, ev):
        print("tx start")
        self.actions.tx_start(ev)
    def output_A_TX_TIMEOUT(self, ev):
        print("tx timeout")
        self.actions.tx_timeout(ev)
    def output_A_UNSHUT(self, ev):
        print("unshutdown")
        self.actions.unshut(ev)
        


si446xDriver = constructFiniteStateMachine(
    inputs=Events,
    outputs=Actions,
    states=States,
    table=table,
    initial=States.S_SDN,
    richInputs=[],
    inputContext={},
    world=MethodSuffixOutputer(Action_code(0)),
)

def cycle():
    si446xDriver.receive(Events.E_TURNON)
    si446xDriver.receive(Events.E_WAIT_DONE)
    si446xDriver.receive(Events.E_WAIT_DONE)
    si446xDriver.receive(Events.E_CONFIG_DONE)
    si446xDriver.receive(Events.E_TURNOFF)
#    si446xDriver.receive(Events.E_WAIT_DONE)


if __name__ == '__main__':
    cycle()

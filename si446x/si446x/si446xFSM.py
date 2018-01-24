from __future__ import print_function   # python3 print function
from builtins import *

all = ['Events', 'Actions', 'States', 'table']

from twisted.python.constants import Names, NamedConstant

from machinist import TransitionTable, MethodSuffixOutputer, constructFiniteStateMachine

table = TransitionTable()

class States(Names):
   S_CONFIG_W = NamedConstant()
   S_POR_W = NamedConstant()
   S_PWR_UP_W = NamedConstant()
   S_RX_ACTIVE = NamedConstant()
   S_RX_ON = NamedConstant()
   S_SDN = NamedConstant()
   S_STANDBY = NamedConstant()
   S_TX_ACTIVE = NamedConstant()
   S_DEFAULT = NamedConstant()

class Events(Names):
   E_0NOP = NamedConstant()
   E_CONFIG_DONE = NamedConstant()
   E_CRC_ERROR = NamedConstant()
   E_INVALID_SYNC = NamedConstant()
   E_PACKET_RX = NamedConstant()
   E_PACKET_SENT = NamedConstant()
   E_PREAMBLE_DETECT = NamedConstant()
   E_RX_THRESH = NamedConstant()
   E_STANDBY = NamedConstant()
   E_SYNC_DETECT = NamedConstant()
   E_TRANSMIT = NamedConstant()
   E_TURNOFF = NamedConstant()
   E_TURNON = NamedConstant()
   E_TX_THRESH = NamedConstant()
   E_WAIT_DONE = NamedConstant()

class Actions(Names):
   A_CLEAR_SYNC = NamedConstant()
   A_CONFIG = NamedConstant()
   A_NOP = NamedConstant()
   A_PWR_DN = NamedConstant()
   A_PWR_UP = NamedConstant()
   A_READY = NamedConstant()
   A_RX_CMP = NamedConstant()
   A_RX_CNT_CRC = NamedConstant()
   A_RX_DRAIN_FF = NamedConstant()
   A_RX_START = NamedConstant()
   A_RX_TIMEOUT = NamedConstant()
   A_STANDBY = NamedConstant()
   A_TX_CMP = NamedConstant()
   A_TX_FILL_FF = NamedConstant()
   A_TX_START = NamedConstant()
   A_TX_TIMEOUT = NamedConstant()
   A_UNSHUT = NamedConstant()


table = table.addTransition(States.S_TX_ACTIVE, Events.E_TX_THRESH, [Actions.A_TX_FILL_FF], States.S_TX_ACTIVE)
table = table.addTransition(States.S_RX_ON, Events.E_INVALID_SYNC, [Actions.A_CLEAR_SYNC], States.S_RX_ON)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_INVALID_SYNC, [Actions.A_CLEAR_SYNC], States.S_RX_ACTIVE)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_PACKET_RX, [Actions.A_RX_CMP], States.S_RX_ON)
table = table.addTransition(States.S_SDN, Events.E_TURNON, [Actions.A_UNSHUT], States.S_POR_W)
table = table.addTransition(States.S_SDN, Events.E_0NOP, [Actions.A_NOP], States.S_SDN)
table = table.addTransition(States.S_STANDBY, Events.E_TURNON, [Actions.A_READY], States.S_RX_ON)
table = table.addTransition(States.S_TX_ACTIVE, Events.E_PACKET_SENT, [Actions.A_TX_CMP], States.S_RX_ON)
table = table.addTransition(States.S_RX_ON, Events.E_TRANSMIT, [Actions.A_TX_START], States.S_TX_ACTIVE)
table = table.addTransition(States.S_CONFIG_W, Events.E_CONFIG_DONE, [Actions.A_READY], States.S_RX_ON)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_RX_THRESH, [Actions.A_RX_DRAIN_FF], States.S_RX_ACTIVE)
table = table.addTransition(States.S_SDN, Events.E_STANDBY, [Actions.A_CONFIG], States.S_STANDBY)
table = table.addTransition(States.S_RX_ON, Events.E_STANDBY, [Actions.A_STANDBY], States.S_STANDBY)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_STANDBY, [Actions.A_STANDBY], States.S_STANDBY)
table = table.addTransition(States.S_TX_ACTIVE, Events.E_STANDBY, [Actions.A_STANDBY], States.S_STANDBY)
table = table.addTransition(States.S_POR_W, Events.E_WAIT_DONE, [Actions.A_PWR_UP], States.S_PWR_UP_W)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_WAIT_DONE, [Actions.A_RX_TIMEOUT], States.S_RX_ON)
table = table.addTransition(States.S_TX_ACTIVE, Events.E_WAIT_DONE, [Actions.A_TX_TIMEOUT], States.S_RX_ON)
table = table.addTransition(States.S_PWR_UP_W, Events.E_WAIT_DONE, [Actions.A_CONFIG], States.S_CONFIG_W)
table = table.addTransition(States.S_DEFAULT, Events.E_0NOP, [Actions.A_NOP], States.S_DEFAULT)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_CRC_ERROR, [Actions.A_RX_CNT_CRC], States.S_RX_ON)
table = table.addTransition(States.S_RX_ON, Events.E_PREAMBLE_DETECT, [Actions.A_NOP], States.S_RX_ON)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_PREAMBLE_DETECT, [Actions.A_NOP], States.S_RX_ACTIVE)
table = table.addTransition(States.S_RX_ON, Events.E_SYNC_DETECT, [Actions.A_RX_START], States.S_RX_ACTIVE)
table = table.addTransition(States.S_RX_ON, Events.E_TURNOFF, [Actions.A_PWR_DN], States.S_SDN)
table = table.addTransition(States.S_RX_ACTIVE, Events.E_TURNOFF, [Actions.A_PWR_DN], States.S_SDN)
table = table.addTransition(States.S_TX_ACTIVE, Events.E_TURNOFF, [Actions.A_PWR_DN], States.S_SDN)
table = table.addTransition(States.S_STANDBY, Events.E_TURNOFF, [Actions.A_PWR_DN], States.S_SDN)

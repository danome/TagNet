
"""
Si446x Packet Driver: Native Python implementation for Si446x Radio Device

@author: Dan Maltbie
"""
__all__ = ['si446xact', 'si446xdef', 'si446xdvr', 'si446xFSM', 'si446xradio', 'si446xcfg', 'si446xtrace']

from si446xdvr import si446x_dbus_interface, reactor_loop

__version__ = '0.0.5'

print 'si446x driver version {}'.format(__version__)

if __name__ == '__main__':
    reactor_loop()

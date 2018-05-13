"""
Si446x Packet Driver: Native Python implementation for Si446x Radio Device

@author: Dan Maltbie
"""

import os,sys
# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# zzz print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('\n'.join(sys.path))

from si446xvers   import __version__
print('si446x version: ', __version__)

try:
    from si446xcfg    import get_config_wds, get_config_device, get_name_wds, wds_config_count, wds_config_str, wds_default_config
except ImportError:
    print('si446x radio configuration shared module needs to be built')
    sys.exit(1)

from si446xact    import *
from si446xdef    import *
from si446xradio  import *
from si446xdvr    import *
from si446xFSM    import *
from si446xtrace  import *

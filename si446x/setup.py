#!/usr/bin/env python
import os, re

DESCRIPTION = 'Packet level driver for Si446x radio chip'
with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
    LONG_DESCRIPTION = f.read()

# get version string from __init__.py file
#
def get_version():
    VERSIONFILE = os.path.join('si446x', 'si446xvers.py')
    initfile_lines = open(VERSIONFILE, 'rt').readlines()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    for line in initfile_lines:
        mo = re.search(VSRE, line, re.M)
        if mo:
            return mo.group(1)
    raise RuntimeError('Unable to find version string in %s.' % (VERSIONFILE,))

try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

# add extension for the c-file containing si446x radion config strings
#
import subprocess
subprocess.call(['make', '-C', 'si446x/radioconfig'])


setup(
    name             = 'si446x',
    version          = get_version(),
    description      = DESCRIPTION,
    license          = ['LICENSE.txt'],
    long_description = LONG_DESCRIPTION,
    url              = 'https://github.com/dmaltbie/Tagnet/si446x',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['future',
                        'machinist',
                        'twisted==13.1.0',
                        'six',
                        'construct==2.5.2',
                        'txdbus==1.1.0',
                        'spidev',
                        'RPi.GPIO'],
    provides         = ['si446x'],
    packages         = ['si446x'],
    package_data     = {'si446x': ['si446xcfg.so']},
    keywords         = ['si446x', 'twisted', 'spidev', 'dbus'],
    classifiers      = ['License :: OSI Approved :: MIT License',
                        'Development Status :: 4 - Beta',
                        'Framework :: Twisted',
                        'Intended Audience :: Developers',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: POSIX',
                        'Programming Language :: Python',
                        'Topic :: Software Development :: Libraries',
                        'Topic :: System :: Networking'],
    )

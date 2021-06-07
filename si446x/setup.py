#!/usr/bin/env python

DESCRIPTION = 'Packet level driver for Si446x radio chip'

# get version string from __init__.py file
#
import os, re
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
config_strings = Extension('si446x/si446xcfg',
                           define_macros = [('__version__', get_version())],
                           include_dirs = ['/usr/local/include',
                                           '/usr/include/python2.7'],
                           library_dirs = ['/usr/local/lib',
                                           '/usr/lib/python2.7'],
                           sources = ['si446x/radioconfig/si446xcfg.c'])

setup(
    name             = 'si446x',
    version          = get_version(),
    description      = DESCRIPTION,
    license          = ['LICENSE.txt'],
    long_description ="""\
Packet level driver for si446x radio chip""",
    url              = 'https://github.com/dmaltbie/Tagnet/si446x',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['future',
                        'machinist',
                        'twisted==20.3.0',
                        'six',
                        'construct==2.5.2',
                        'txdbus==1.1.0'],
    provides         = ['si446x'],
    packages         = ['si446x',
                        'si446x.test'],
    ext_modules      = [config_strings],
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

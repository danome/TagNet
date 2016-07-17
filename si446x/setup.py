#!/usr/bin/env python

VERSION     = '0.0.03'
DESCRIPTION = 'Packet level driver for Si446x radio chip'

import os, re
def get_version():
    VERSIONFILE = os.path.join('si446x', '__init__.py')
    initfile_lines = open(VERSIONFILE, 'rt').readlines()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    for line in initfile_lines:
        print line
        mo = re.search(VSRE, line, re.M)
        if mo:
            return mo.group(1)
    raise RuntimeError('Unable to find version string in %s.' % (VERSIONFILE,))

try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

config_strings = Extension('si446x/si446xcfg',
                           define_macros = [('MAJOR_VERSION', '1'),
                                            ('MINOR_VERSION', '0')],
                           include_dirs = ['/usr/local/include'],
#                           libraries = ['tcl83'],
                           library_dirs = ['/usr/local/lib'],
                           sources = ['si446x/radioconfig/si446xcfg.c'])

setup(
    name             = 'si446x',
    version          = get_version(),
    description      = DESCRIPTION,
    license          = "MIT",
    long_description ="""\
Packet level driver for Si446x radio chip""",
    url              = 'https://github.com/dmaltbie/Tagnet/si446x',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['twisted>=10.1', 'six'],
    provides         = ['si446x'],
    packages         = ['si446x',
                        'si446x.test'],
    ext_modules      = [config_strings],
    keywords         = ['si446x', 'twisted', 'spidev', 'dbus'],
    classifiers      = ['Development Status :: 4 - Beta',
                        'Framework :: Twisted',
                        'Intended Audience :: Developers',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: POSIX',
                        'Programming Language :: Python',
                        'Topic :: Software Development :: Libraries',
                        'Topic :: System :: Networking'],
    )


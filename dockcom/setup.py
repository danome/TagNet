#!/usr/bin/env python

DESCRIPTION = 'Packet level driver for Dockcom serial(SPI) link'

import os, re
def get_version():
    VERSIONFILE = os.path.join('dockcom', '__init__.py')
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

config_strings = Extension('dockcom/dockcomcfg',
                           define_macros = [('MAJOR_VERSION', '1'),
                                            ('MINOR_VERSION', '0')],
                           include_dirs = ['/usr/local/include'],
                           library_dirs = ['/usr/local/lib'],
                           sources = ['dockcom/radioconfig/dockcomcfg.c'])

setup(
    name             = 'dockcom',
    version          = get_version(),
    description      = DESCRIPTION,
    license          = "MIT",
    long_description ="""\
Packet level driver for Dockcom radio chip""",
    url              = 'https://github.com/dmaltbie/Tagnet/dockcom',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['twisted>=10.1', 'six'],
    provides         = ['dockcom'],
    packages         = ['dockcom',
                        'dockcom.test'],
    ext_modules      = [config_strings],
    keywords         = ['dockcom', 'twisted', 'spidev', 'dbus'],
    classifiers      = ['Development Status :: 4 - Beta',
                        'Framework :: Twisted',
                        'Intended Audience :: Developers',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: POSIX',
                        'Programming Language :: Python',
                        'Topic :: Software Development :: Libraries',
                        'Topic :: System :: Networking'],
    )


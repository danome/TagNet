#!/usr/bin/env python

VERSION     = '1.0.00'
DESCRIPTION = 'Packet level driver for Si446x radio chip'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name             = 'si446x',
    version          = VERSION,
    description      = DESCRIPTION,
    license          = "MIT",
    long_description ="""\
Packet level driver for Si446x radio chip""",
    url              = 'https://github.com/dmaltbie/tagsi446x',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['twisted>=10.1', 'six'],
    provides         = ['si446x'],
    packages         = ['si446x',
                        'xi446x.test'],
    keywords         = ['xxx', 'twisted', 'spidev', 'dbus'],
    classifiers      = ['Development Status :: 4 - Beta',
                        'Framework :: Twisted',
                        'Intended Audience :: Developers',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: POSIX',
                        'Programming Language :: Python',
                        'Topic :: Software Development :: Libraries',
                        'Topic :: System :: Networking'],
    )


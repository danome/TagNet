#!/usr/bin/env python
import os, re

DESCRIPTION = 'FUSE file driver for access tagnet Dblk storage'
with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
    LONG_DESCRIPTION = f.read()

def get_version():
    VERSIONFILE = os.path.join('tagfuse', 'tagfuseargs.py')
    initfile_lines = open(VERSIONFILE, 'rt').readlines()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    for line in initfile_lines:
        mo = re.search(VSRE, line, re.M)
        if mo:
            return mo.group(1)
    raise RuntimeError('Unable to find version string in %s.' % (VERSIONFILE,))

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name             = 'tagfuse',
    version          = get_version(),
    long_description = LONG_DESCRIPTION,
    license          = ['LICENSE.txt'],
    url              = 'https://github.com/dmaltbie/Tagnet/tagfuse',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['twisted>=13.1.0',
                        'six',
                        'chest',
                        'construct',
                        'uuid',
                        'datetime',
                        'future',
                        'enum34'],
    provides         = ['tagfuse'],
    packages         = ['tagfuse'],
    keywords         = ['tagfuse', 'twisted', 'dbus'],
    classifiers      = ['Development Status :: 4 - Beta',
                        'Framework :: Twisted',
                        'Intended Audience :: Developers',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: POSIX',
                        'Programming Language :: Python',
                        'Topic :: Software Development :: Libraries',
                        'Topic :: System :: Networking'],
    entry_points     = {
        'console_scripts': ['tagfuse=tagfuse.__main__:main'],
    },
    package_data     = {
        'tagfuse.': ['*.md'],
    },
)

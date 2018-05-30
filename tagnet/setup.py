#!/usr/bin/env python
import os, re

DESCRIPTION = 'tagnet protocol'
with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
    LONG_DESCRIPTION = f.read()

def get_version():
    VERSIONFILE = os.path.join('tagnet', '__init__.py')
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
    name             = 'tagnet',
    version          = get_version(),
    description      = DESCRIPTION,
    license          = 'LICENSE.txt',
    long_description = LONG_DESCRIPTION,
    url              = 'https://github.com/dmaltbie/Tagnet/tagnet',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['twisted>=10.1',
                        'six',
                        'construct==2.5.2',
                        'uuid',
                        'datetime',
                        'future',
                        'enum34'],
    provides         = ['tagnet'],
    packages         = ['tagnet'],
    keywords         = ['tagnet', 'twisted', 'dbus'],
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

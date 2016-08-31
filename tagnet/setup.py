#!/usr/bin/env python

DESCRIPTION = 'tagnet protocol'

import os, re
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
    license          = "MIT",
    long_description ="""\
A protocol transferring of named data objects in an ad hoc network of constraint-based nodes using low-power 400MHz radio networks.""",
    url              = 'https://github.com/dmaltbie/Tagnet/tagnet',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['twisted>=10.1', 'six', 'temporenc', 'construct', 'uuid', 'datetime', 'platform'],
    provides         = ['tagnet'],
    packages         = ['tagnet',
                        'tagnet.test'],
    keywords         = ['tagnet', 'twisted', 'dbus'],
    classifiers      = ['Development Status :: 4 - Beta',
                        'Framework :: Twisted',
                        'Intended Audience :: Developers',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: POSIX',
                        'Programming Language :: Python',
                        'Topic :: Software Development :: Libraries',
                        'Topic :: System :: Networking'],
    )


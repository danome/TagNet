#!/usr/bin/env python

VERSION     = '1.0.00'
DESCRIPTION = 'template description'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name             = 'template',
    version          = VERSION,
    description      = DESCRIPTION,
    license          = "MIT",
    long_description ="""\
template description""",
    url              = 'https://github.com/dmaltbie/template',
    author           = 'Dan Maltbie',
    author_email     = 'dmaltbie@daloma.org',
    install_requires = ['twisted>=10.1', 'six'],
    provides         = ['template'],
    packages         = ['template',
                        'template.test'],
    keywords         = ['template', 'twisted'],
    classifiers      = ['Development Status :: 4 - Beta',
                        'Framework :: Twisted',
                        'Intended Audience :: Developers',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: POSIX',
                        'Programming Language :: Python',
                        'Topic :: Software Development :: Libraries',
                        'Topic :: System :: Networking'],
    )


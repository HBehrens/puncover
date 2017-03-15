#!/usr/bin/env python
from setuptools import setup, find_packages

__version__ = None  # Overwritten by executing version.py.
with open('puncover/version.py') as f:
    exec (f.read())

requires = [
    'Flask==0.10.1\n'
    'mock==1.3.0\n',
]

setup(name='puncover',
      version=__version__,
      description='Analyses C/C++ build output for code size, static variables, and stack usage.',
      long_description=open('README.rst').read(),
      url='https://github.com/hbehrens/puncover',
      download_url='https://github.com/hbehrens/puncover/tarball/%s' % __version__,
      author='Heiko Behrens',
      license='MIT',
      packages=find_packages(exclude=['tests', 'tests.*']),
      entry_points={'console_scripts': ['puncover = puncover.puncover:main']},
      install_requires=requires,
      test_suite='nose.collector',
      )

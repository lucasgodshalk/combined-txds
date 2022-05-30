#!/usr/bin/env python

from setuptools import setup # could also use distutils.core

setup(name='ANOEDS',
      version='0.2',
      description='Analyze Network Operations of Electrical Distribution Systems',
      author='Arnav Gautam',
      author_email='arnavjgautam@gmail.com',
      packages=['anoeds'],
      license='MIT',
      install_requires=[
        'numpy>=1.21.2',
        'pandas>=1.3.2',
        'sympy>=1.9',
        'scipy>=1.7.1',
        'pytest',
        'click',
        'future',
        'json_tricks',
        'networkx',
        'six',
        'traitlets',
        'croniter',
      ],
      tests_require=[
        'pytest'
      ]
     )
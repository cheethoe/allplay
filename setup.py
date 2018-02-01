#!/usr/bin/env python
from setuptools import setup
setup(name='allplay',
      version='0.1.0',
      description='Manage while you consume media manager',
      author='Michael Hsu',
      author_email='cheeto@gmail.com',
      url='https://github.com/cheethoe/allplay'
      install_requires=['boto3',
                        'collections',
                        'copy',
                        'datetime',
                        'future',
                        'logging',
                        'os',
                        'random',
                        'shutil',
                        'sqlite3',
                        'subprocess',
                        'sys',
                        'tzlocal',
                        'yaml'
                       ]
)

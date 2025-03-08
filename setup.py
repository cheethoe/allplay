#!/usr/bin/env python
from setuptools import setup
setup(name='allplay',
      version='0.2.0',
      description='Manage while you consume media manager',
      author='Michael Hsu',
      author_email='cheeto@gmail.com',
      url='https://github.com/cheethoe/allplay',
      install_requires=['boto3>=1.37.9',
                        'future>=1.0.0',
                        'tzlocal>=5.3.1',
                        'pyyaml>=6.0.2'],
     packages=['allplay'],
     entry_points={
         'console_scripts': ['allplay=allplay.allplay:main']
         },
)

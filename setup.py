from setuptools import setup

from twisted.python.dist import getPackages

setup(
    name='tryfer',
    version='0.1',
    description='Twisted Zipkin Tracing Library',
    packages=getPackages('tryfer'),
    install_requires=['Twisted', 'thrift', 'scrivener'],
)

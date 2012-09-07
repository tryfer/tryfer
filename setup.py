import os
from setuptools import setup


def getPackages(base):
    packages = []

    def visit(arg, directory, files):
        if '__init__.py' in files:
            packages.append(directory.replace('/', '.'))

    os.path.walk(base, visit, None)

    return packages

setup(
    name='tryfer',
    version='0.1',
    description='Twisted Zipkin Tracing Library',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Framework :: Twisted'
    ],
    maintainer='David Reid',
    maintainer_email='david.reid@rackspace.com',
    license='APL2',
    url='https://github.com/racker/tryfer',
    long_description=open('README.rst').read(),
    packages=getPackages('tryfer'),
    install_requires=[
        'Twisted >= 12.0.0',
        'thrift == 0.8.0',
        'scrivener == 0.2'
    ],
)

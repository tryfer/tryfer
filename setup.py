from setuptools import setup, find_packages

setup(
    name='tryfer',
    version='0.2.1',
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
    packages=find_packages('.'),
    install_requires=[
        'Twisted >= 12.0.0',
        'thrift == 0.8.0',
        'scrivener == 0.2'
    ],
)

from distutils.core import setup
from twisted.python.dist import getPackages


def refresh_plugin_cache():
    from twisted.plugin import IPlugin, getPlugins
    list(getPlugins(IPlugin))

setup(name='tryfer',
      version='0.1',
      description='Twisted Zipkin Tracing Library',
      packages=getPackages('tryfer'))

refresh_plugin_cache()

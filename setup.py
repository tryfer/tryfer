from distutils.core import setup


def refresh_plugin_cache():
    from twisted.plugin import IPlugin, getPlugins
    list(getPlugins(IPlugin))

setup(name='tryfer',
      version='0.1',
      description='Twisted Zipkin Tracing Library',
      packages=['tryfer', 'tryfer._thrift', 'tryfer.tests'])

refresh_plugin_cache()

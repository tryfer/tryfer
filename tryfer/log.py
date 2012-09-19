from twisted.python import log

_debugging = False


def set_debugging(on=True):
    global _debugging
    _debugging = on


def debug(*args, **kwargs):
    if _debugging:
        kwargs['logLevel'] = 'DEBUG'
        if 'format' in kwargs:
            kwargs['format'] = '%(logLevel)s: ' + kwargs['format']

        else:
            args[0] = '%s: %s' % (kwargs['logLevel'], args[0])

        log.msg(*args, **kwargs)


msg = log.msg
err = log.err

from unittest import skipIf

_twisted = None
try:
    import twisted as _twisted
except ImportError:
    pass

hasTwisted = _twisted is not None

skipWithoutTwisted = skipIf(not hasTwisted, "Twisted is not installed.")

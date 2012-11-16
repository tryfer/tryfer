from unittest import skipIf

try:
    import twisted
    hasTwisted = True
except ImportError:
    hasTwisted = False

skipWithoutTwisted = skipIf(not hasTwisted, "Twisted is not installed.")

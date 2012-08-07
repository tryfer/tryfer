from twisted.trial.unittest import TestCase

from tryfer.tracers import get_tracer, set_tracer


class GlobalTracerTests(TestCase):
    def test_get_set_tracer(self):
        dummy_tracer = object()

        self.assertEqual(get_tracer(), None)

        set_tracer(dummy_tracer)
        self.assertEqual(get_tracer(), dummy_tracer)

from twisted.trial.unittest import TestCase

from tryfer.tracers import get_tracers, set_tracers, push_tracer


class GlobalTracerTests(TestCase):
    def tearDown(self):
        set_tracers([])

    def test_set_tracers(self):
        dummy_tracer = object()

        set_tracers([dummy_tracer])
        self.assertEqual(get_tracers(), [dummy_tracer])

    def test_push_tracer(self):
        dummy_tracer = object()
        dummy_tracer2 = object()

        push_tracer(dummy_tracer)
        self.assertEqual(get_tracers(), [dummy_tracer])

        push_tracer(dummy_tracer2)

        self.assertEqual(get_tracers(), [dummy_tracer, dummy_tracer2])

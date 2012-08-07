import math

import mock

from twisted.trial.unittest import TestCase

from tryfer.trace import Trace, Annotation, Endpoint

MAX_ID = math.pow(2, 31) - 1


class TraceTests(TestCase):
    def test_new_Trace(self):
        t = Trace('test_trace')
        self.assertNotEqual(t.trace_id, None)
        self.assertIsInstance(t.trace_id, int)
        self.failIf(t.trace_id >= MAX_ID)

        self.assertNotEqual(t.span_id, None)
        self.assertIsInstance(t.span_id, int)
        self.failIf(t.span_id >= MAX_ID)

        self.assertEqual(t.parent_span_id, None)

    def test_Trace_child(self):
        t = Trace('test_trace', trace_id=1, span_id=1)

        c = t.child('child_test_trace')

        self.assertEqual(c.trace_id, 1)
        self.assertEqual(c.parent_span_id, 1)
        self.assertNotEqual(c.span_id, 1)

    def test_record_invokes_tracer(self):
        tracer = mock.Mock()

        t = Trace('test_trace', trace_id=1, span_id=1, tracer=tracer)
        annotation = Annotation.client_send(timestamp=0)
        t.record(annotation)

        tracer.record.assert_called_with(t, annotation)

    def test_record_sets_annotation_endpoint(self):
        tracer = mock.Mock()
        web_endpoint = Endpoint('127.0.0.1', 8080, 'web')

        t = Trace('test_trace', trace_id=1, span_id=1, tracer=tracer)
        t.set_endpoint(web_endpoint)
        annotation = Annotation.client_send(timestamp=1)
        t.record(annotation)

        tracer.record.assert_called_with(t, annotation)

        self.assertEqual(annotation.endpoint, web_endpoint)


class AnnotationTests(TestCase):
    def setUp(self):
        self.time_patcher = mock.patch('tryfer.trace.time.time')
        self.time = self.time_patcher.start()
        self.time.return_value = 1

    def tearDown(self):
        self.time_patcher.stop()

    def test_timestamp(self):
        a = Annotation.timestamp('test')
        self.assertEqual(a.value, 1000000)
        self.assertEqual(a.name, 'test')
        self.assertEqual(a.annotation_type, 'timestamp')

    def test_client_send(self):
        a = Annotation.client_send()
        self.assertEqual(a.value, 1000000)
        self.assertEqual(a.name, 'cs')
        self.assertEqual(a.annotation_type, 'timestamp')

    def test_cleint_recv(self):
        a = Annotation.client_recv()
        self.assertEqual(a.value, 1000000)
        self.assertEqual(a.name, 'cr')
        self.assertEqual(a.annotation_type, 'timestamp')

    def test_server_send(self):
        a = Annotation.server_send()
        self.assertEqual(a.value, 1000000)
        self.assertEqual(a.name, 'ss')
        self.assertEqual(a.annotation_type, 'timestamp')

    def test_server_recv(self):
        a = Annotation.server_recv()
        self.assertEqual(a.value, 1000000)
        self.assertEqual(a.name, 'sr')
        self.assertEqual(a.annotation_type, 'timestamp')

import json
import Queue

import mock

from unittest2 import TestCase

from zope.interface.verify import verifyObject

from tryfer.interfaces import ITracer

from tryfer.trace import Trace, Annotation

from tryfer.py.tracers import (
    RawZipkinTracer,
    RawRESTkinScribeTracer,
    RawRESTkinHTTPTracer,
    ThreadedBufferingTracer
)


class RawZipkinTracerTests(TestCase):
    def setUp(self):
        self.scribe = mock.Mock()

    def test_verifyObject(self):
        verifyObject(ITracer, RawZipkinTracer(self.scribe))

    def test_logs_to_scribe_immediately(self):
        tracer = RawZipkinTracer(self.scribe)
        t = Trace('test_raw_zipkin', 1, 2, tracers=[tracer])

        t.record(Annotation.client_send(1))
        self.scribe.log.assert_called_once_with(
            'zipkin',
            ['CgABAAAAAAAAAAELAAMAAAAPdGVzdF9yYXdfemlwa2luCgAEAAAAAAAAAAIPAAY'
             'MAAAAAQoAAQAA\nAAAAAAABCwACAAAAAmNzAA8ACAwAAAAAAA=='])

    def test_logs_to_scribe(self):
        tracer = RawZipkinTracer(self.scribe)
        t = Trace('test_raw_zipkin', 1, 2, tracers=[tracer])

        t.record(Annotation.client_send(1), Annotation.client_recv(2))

        self.scribe.log.assert_called_once_with(
            'zipkin',
            ['CgABAAAAAAAAAAELAAMAAAAPdGVzdF9yYXdfemlwa2luCgAEAAAAAAAAAAIPAAY'
             'MAAAAAgoAAQAA\nAAAAAAABCwACAAAAAmNzAAoAAQAAAAAAAAACCwACAAAAAmNy'
             'AA8ACAwAAAAAAA=='])

    def test_logs_to_scribe_with_non_default_category(self):
        tracer = RawZipkinTracer(self.scribe, 'not-zipkin')
        t = Trace('test_raw_zipkin', 1, 2, tracers=[tracer])

        t.record(Annotation.client_send(1), Annotation.client_recv(2))

        self.scribe.log.assert_called_once_with(
            'not-zipkin',
            ['CgABAAAAAAAAAAELAAMAAAAPdGVzdF9yYXdfemlwa2luCgAEAAAAAAAAAAIPAAY'
             'MAAAAAgoAAQAA\nAAAAAAABCwACAAAAAmNzAAoAAQAAAAAAAAACCwACAAAAAmNy'
             'AA8ACAwAAAAAAA=='])

    def test_handles_batched_traces(self):
        tracer = RawZipkinTracer(self.scribe)
        t1 = Trace('test_raw_zipkin', 1, 2, tracers=[tracer])

        cs1 = Annotation.client_send(1)

        t2 = Trace('test_raw_zipkin', 1, 2, tracers=[tracer])

        cs2 = Annotation.client_send(1)
        cr2 = Annotation.client_recv(2)

        tracer.record([(t1, [cs1]), (t2, [cs2, cr2])])

        self.scribe.log.assert_called_once_with(
            'zipkin',
            ['CgABAAAAAAAAAAELAAMAAAAPdGVzdF9yYXdfemlwa2luCgAEAAAAAAAAAAIPAAY'
             'MAAAAAQoAAQAA\nAAAAAAABCwACAAAAAmNzAA8ACAwAAAAAAA==',
             'CgABAAAAAAAAAAELAAMAAAAPdGVzdF9yYXdfemlwa2luCgAEAAAAAAAAAAIPAAY'
             'MAAAAAgoAAQAA\nAAAAAAABCwACAAAAAmNzAAoAAQAAAAAAAAACCwACAAAAAmNy'
             'AA8ACAwAAAAAAA=='])


def json_matcher(expected):
    class _matcher(object):
        def __eq__(self, other):
            return json.loads(other) == expected

    return _matcher()


class RawRESTkinScribeTracerTests(TestCase):
    def setUp(self):
        self.scribe = mock.Mock()
        self.tracer = RawRESTkinScribeTracer(self.scribe)

    def test_verifyObject(self):
        verifyObject(ITracer, self.tracer)

    def test_traces_immediately(self):
        t = Trace('test', 1, 2, tracers=[self.tracer])
        t.record(Annotation.client_send(1))

        self.scribe.log.assert_called_once_with(
            'restkin',
            [json_matcher(
                [{'trace_id': '0000000000000001',
                 'span_id': '0000000000000002',
                 'name': 'test',
                 'annotations': [
                     {'type': 'timestamp', 'value': 1, 'key': 'cs'}]}])])

    def test_handles_batched_traces(self):
        t1 = Trace('test', 1, 2)
        t2 = Trace('test2', 3, 4)

        cs1 = Annotation.client_send(1)
        cs2 = Annotation.client_send(2)
        cr1 = Annotation.client_recv(3)
        cr2 = Annotation.client_recv(4)

        self.tracer.record([(t1, [cs1, cr1]), (t2, [cs2, cr2])])

        self.scribe.log.assert_called_once_with(
            'restkin',
            [json_matcher(
                [{'trace_id': '0000000000000001',
                  'span_id': '0000000000000002',
                  'name': 'test',
                  'annotations': [
                      {'type': 'timestamp', 'value': 1, 'key': 'cs'},
                      {'type': 'timestamp', 'value': 3, 'key': 'cr'}]},
                 {'trace_id': '0000000000000003',
                  'span_id': '0000000000000004',
                  'name': 'test2',
                  'annotations': [
                      {'type': 'timestamp', 'value': 2, 'key': 'cs'},
                      {'type': 'timestamp', 'value': 4, 'key': 'cr'}]}])])


class RawRESTkinHTTPTracerTests(TestCase):
    def setUp(self):
        self.requests_patcher = mock.patch('tryfer.py.tracers.requests')
        self.requests = self.requests_patcher.start()
        self.addCleanup(self.requests_patcher.stop)

        self.tracer = RawRESTkinHTTPTracer('http://trace.it')
        self.trace = Trace('test', 1, 2, tracers=[self.tracer])

    def test_verifyObject(self):
        verifyObject(ITracer, self.tracer)

    def test_posts_immediately(self):
        self.trace.record(Annotation.client_send(1))

        self.requests.post.assert_called_once_with(
            'http://trace.it',
            json_matcher(
                [{'trace_id': '0000000000000001',
                  'span_id': '0000000000000002',
                  'name': 'test',
                  'annotations': [
                      {'type': 'timestamp', 'value': 1, 'key': 'cs'}
                  ]}]))

    def test_handles_batched_traces(self):
        t1 = self.trace
        t2 = Trace('test2', 3, 4)

        cs1 = Annotation.client_send(1)
        cs2 = Annotation.client_send(2)
        cr1 = Annotation.client_recv(3)
        cr2 = Annotation.client_recv(4)

        self.tracer.record([(t1, [cs1, cr1]), (t2, [cs2, cr2])])

        self.requests.post.assert_called_once_with(
            'http://trace.it',
            json_matcher(
                [{'trace_id': '0000000000000001',
                  'span_id': '0000000000000002',
                  'name': 'test',
                  'annotations': [
                      {'type': 'timestamp', 'value': 1, 'key': 'cs'},
                      {'type': 'timestamp', 'value': 3, 'key': 'cr'}
                  ]},
                 {'trace_id': '0000000000000003',
                  'span_id': '0000000000000004',
                  'name': 'test2',
                  'annotations': [
                      {'type': 'timestamp', 'value': 2, 'key': 'cs'},
                      {'type': 'timestamp', 'value': 4, 'key': 'cr'}
                  ]}]))


_empty = object()


class ThreadedBufferingTracerTests(TestCase):
    def setUp(self):
        self.mock_tracer = mock.Mock()
        self.trace_queue = Queue.Queue()

        def _mock_record(*args, **kwargs):
            self.trace_queue.put(None)

        self.mock_tracer.record.side_effect = _mock_record

        self.in_queue = Queue.Queue()
        self.out_queue = Queue.Queue()

        self.mock_queue_patcher = mock.patch("tryfer.py.tracers.Queue.Queue")
        self.mock_queue = self.mock_queue_patcher.start().return_value

        def _mock_get(*args, **kwargs):
            if 'timeout' in kwargs:
                del kwargs['timeout']
            item = self.out_queue.get(*args, **kwargs)

            if item == _empty:
                raise Queue.Empty()

            return item

        self.mock_queue.get.side_effect = _mock_get

        def _mock_put(*args, **kwargs):
            return self.in_queue.put(*args, **kwargs)

        self.mock_queue.put.side_effect = _mock_put

        self.tracer = ThreadedBufferingTracer(self.mock_tracer, 2, 10)
        self.trace = Trace('test', 1, 2, tracers=[self.tracer])

    def tearDown(self):
        self.mock_queue_patcher.stop()

    def pump(self):
        self.out_queue.put(self.in_queue.get(block=True))

    def wait(self):
        self.trace_queue.get(block=True, timeout=10)

    def test_max_traces_record(self):
        a1 = Annotation.client_send(1)
        a2 = Annotation.client_recv(2)

        self.trace.record(a1)

        self.assertEqual(self.mock_queue.put.call_count, 0)

        self.trace.record(a2)

        self.mock_queue.put.assert_called_once_with(None)

        self.pump()
        self.wait()

        self.mock_tracer.record.assert_called_once_with(
            [(self.trace, (a1,)), (self.trace, (a2,))]
        )

    def test_send_interval_record(self):
        a1 = Annotation.client_send(1)

        self.trace.record(a1)

        self.assertEqual(self.mock_queue.put.call_count, 0)

        self.out_queue.put(_empty)
        self.wait()

        self.mock_tracer.record.assert_called_once_with(
            [(self.trace, (a1,))]
        )

# Copyright 2012 Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from StringIO import StringIO

import json

import mock

from zope.interface.verify import verifyObject

from twisted.trial.unittest import TestCase
from twisted.web.http_headers import Headers
from twisted.web.test.test_webclient import FileConsumer

from tryfer.tracers import get_tracers, set_tracers, push_tracer
from tryfer.tracers import (
    EndAnnotationTracer,
    RawZipkinTracer,
    ZipkinTracer,
    RawRESTkinHTTPTracer,
    RESTkinHTTPTracer,
    RawRESTkinScribeTracer,
    RESTkinScribeTracer,
    DebugTracer
)

from tryfer.interfaces import ITracer

from tryfer.trace import Trace, Annotation


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


class EndAnnotationTracerTests(TestCase):
    def setUp(self):
        self.tracer = mock.Mock()

    def test_verifyObject(self):
        verifyObject(ITracer, EndAnnotationTracer(self.tracer))

    def test_delegates_on_end_annotation(self):
        tracer = EndAnnotationTracer(self.tracer)

        t = Trace('test_delegation', tracers=[tracer])

        cs = Annotation.client_send()
        ce = Annotation.client_recv()

        t.record(cs)
        t.record(ce)

        self.tracer.record.assert_called_once_with([(t, [cs, ce])])

    def test_non_default_end(self):
        tracer = EndAnnotationTracer(self.tracer, end_annotations=['timeout'])

        t = Trace('test_non-default', tracers=[tracer])

        cs = Annotation.client_send()

        t.record(cs)

        timeout = Annotation.timestamp('timeout')

        t.record(timeout)

        self.tracer.record.assert_called_once_with([(t, [cs, timeout])])

    def test_handles_batched_traces(self):
        tracer = EndAnnotationTracer(self.tracer)

        t1 = Trace('test1', tracers=[tracer])
        t2 = Trace('test2', tracers=[tracer])

        cs1 = Annotation.client_send()
        cs2 = Annotation.client_send()

        cr1 = Annotation.client_recv()
        cr2 = Annotation.client_recv()

        tracer.record([(t1, [cs1, cr1]), (t2, [cs2, cr2])])

        self.assertEqual(self.tracer.record.call_count, 2)

        self.tracer.record.assert_any_call([(t1, [cs1, cr1])])
        self.tracer.record.assert_any_call([(t2, [cs2, cr2])])


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


class ZipkinTracerTests(TestCase):
    def setUp(self):
        self.scribe = mock.Mock()

    def test_verifyObject(self):
        verifyObject(ITracer, ZipkinTracer(self.scribe))

    def test_logs_at_end(self):
        tracer = ZipkinTracer(self.scribe)
        t = Trace('test_raw_zipkin', 1, 2, tracers=[tracer])

        t.record(Annotation.client_send(1), Annotation.client_recv(2))

        self.scribe.log.assert_called_once_with(
            'zipkin',
            ['CgABAAAAAAAAAAELAAMAAAAPdGVzdF9yYXdfemlwa2luCgAEAAAAAAAAAAIPAAY'
             'MAAAAAgoAAQAA\nAAAAAAABCwACAAAAAmNzAAoAAQAAAAAAAAACCwACAAAAAmNy'
             'AA8ACAwAAAAAAA=='])

    def test_doesnt_log_immediately(self):
        tracer = ZipkinTracer(self.scribe)
        t = Trace('test_raw_zipkin', 1, 2, tracers=[tracer])

        t.record(Annotation.client_send(1))

        self.assertEqual(self.scribe.log.call_count, 0)


class _HTTPTestMixin(object):
    def assertBodyEquals(self, bodyProducer, expectedOutput):
        output = StringIO()
        consumer = FileConsumer(output)

        def _check_body(_):
            self.assertEqual(
                json.loads(output.getvalue()),
                expectedOutput
            )

        d = bodyProducer.startProducing(consumer)
        d.addCallback(_check_body)

        return d


class RawRESTkinHTTPTracerTests(TestCase, _HTTPTestMixin):
    def setUp(self):
        self.agent = mock.Mock()

        self.tracer = RawRESTkinHTTPTracer(self.agent, 'http://trace.it')
        self.trace = Trace('test', 1, 2, tracers=[self.tracer])

    def test_verifyObject(self):
        verifyObject(ITracer, self.tracer)

    def test_posts_immediately(self):
        self.trace.record(Annotation.client_send(1))

        self.assertEqual(self.agent.request.call_count, 1)

        args = self.agent.request.mock_calls[0][1]
        self.assertEqual(('POST', 'http://trace.it', Headers({})), args[:3])

        bodyProducer = args[3]

        return self.assertBodyEquals(
            bodyProducer,
            [{'trace_id': '0000000000000001',
              'span_id': '0000000000000002',
              'name': 'test',
              'annotations': [
                  {'type': 'timestamp', 'value': 1, 'key': 'cs'}
              ]}])

    def test_handles_batched_traces(self):
        t1 = self.trace
        t2 = Trace('test2', 3, 4)

        cs1 = Annotation.client_send(1)
        cs2 = Annotation.client_send(2)
        cr1 = Annotation.client_recv(3)
        cr2 = Annotation.client_recv(4)

        self.tracer.record([(t1, [cs1, cr1]), (t2, [cs2, cr2])])

        self.assertEqual(self.agent.request.call_count, 1)

        args = self.agent.request.mock_calls[0][1]
        self.assertEqual(('POST', 'http://trace.it', Headers({})), args[:3])

        bodyProducer = args[3]

        return self.assertBodyEquals(
            bodyProducer,
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
              ]}])


class RESTkinHTTPTracerTests(TestCase, _HTTPTestMixin):
    def setUp(self):
        self.agent = mock.Mock()

        self.tracer = RESTkinHTTPTracer(self.agent, 'http://trace.it')
        self.trace = Trace('test', 1, 2, tracers=[self.tracer])

    def test_verifyObject(self):
        verifyObject(ITracer, self.tracer)

    def test_doesnt_post_immediately(self):
        self.trace.record(Annotation.client_send(1))

        self.assertEqual(self.agent.request.call_count, 0)

    def test_posts_at_end(self):
        self.trace.record(Annotation.client_send(1))
        self.trace.record(Annotation.client_recv(2))

        self.assertEqual(self.agent.request.call_count, 1)

        args = self.agent.request.mock_calls[0][1]
        self.assertEqual(('POST', 'http://trace.it', Headers({})), args[:3])

        bodyProducer = args[3]

        return self.assertBodyEquals(
            bodyProducer,
            [{'trace_id': '0000000000000001',
              'span_id': '0000000000000002',
              'name': 'test',
              'annotations': [
                  {'type': 'timestamp', 'value': 1, 'key': 'cs'},
                  {'type': 'timestamp', 'value': 2, 'key': 'cr'}]}])


class RawRESTkinScribeTracerTests(TestCase):
    def setUp(self):
        self.scribe = mock.Mock()
        self.tracer = RawRESTkinScribeTracer(self.scribe)

    def test_verifyObject(self):
        verifyObject(ITracer, self.tracer)

    def test_traces_immediately(self):
        t = Trace('test', 1, 2, tracers=[self.tracer])
        t.record(Annotation.client_send(1))

        self.assertEqual(self.scribe.log.call_count, 1)

        args = self.scribe.log.mock_calls[0][1]

        self.assertEqual('restkin', args[0])
        entries = args[1]
        self.assertEqual(len(entries), 1)

        self.assertEqual(
            json.loads(entries[0]),
            [{'trace_id': '0000000000000001',
              'span_id': '0000000000000002',
              'name': 'test',
              'annotations': [
                  {'type': 'timestamp', 'value': 1, 'key': 'cs'}]}])

    def test_handles_batched_traces(self):
        t1 = Trace('test', 1, 2)
        t2 = Trace('test2', 3, 4)

        cs1 = Annotation.client_send(1)
        cs2 = Annotation.client_send(2)
        cr1 = Annotation.client_recv(3)
        cr2 = Annotation.client_recv(4)

        self.tracer.record([(t1, [cs1, cr1]), (t2, [cs2, cr2])])

        self.assertEqual(self.scribe.log.call_count, 1)

        args = self.scribe.log.mock_calls[0][1]

        self.assertEqual('restkin', args[0])
        entries = args[1]
        self.assertEqual(len(entries), 1)

        self.assertEqual(
            json.loads(entries[0]),
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
              ]}])


class RESTkinScribeTracerTests(TestCase):
    def setUp(self):
        self.scribe = mock.Mock()

        self.tracer = RESTkinScribeTracer(self.scribe)
        self.trace = Trace('test', 1, 2, tracers=[self.tracer])

    def test_verifyObject(self):
        verifyObject(ITracer, self.tracer)

    def test_doesnt_post_immediately(self):
        self.trace.record(Annotation.client_send(1))

        self.assertEqual(self.scribe.log.call_count, 0)

    def test_posts_at_end(self):
        self.trace.record(Annotation.client_send(1))
        self.trace.record(Annotation.client_recv(2))

        self.assertEqual(self.scribe.log.call_count, 1)

        args = self.scribe.log.mock_calls[0][1]

        self.assertEqual('restkin', args[0])
        entries = args[1]
        self.assertEqual(len(entries), 1)

        self.assertEqual(
            json.loads(entries[0]),
            [{'trace_id': '0000000000000001',
              'span_id': '0000000000000002',
              'name': 'test',
              'annotations': [
                  {'type': 'timestamp', 'value': 1, 'key': 'cs'},
                  {'type': 'timestamp', 'value': 2, 'key': 'cr'}
              ]}])


class DebugTracerTests(TestCase):
    def setUp(self):
        self.destination = StringIO()
        self.tracer = DebugTracer(self.destination)

    def test_verifyObject(self):
        verifyObject(ITracer, self.tracer)

    def test_default_destination(self):
        tracer = DebugTracer()
        self.assertEqual(tracer.destination, sys.stdout)

    def test_writes_trace(self):
        t = Trace('test', 1, 2, tracers=[self.tracer])
        t.record(Annotation.client_send(1))

        self.assertEqual(
            json.loads(self.destination.getvalue()),
            [{'trace_id': '0000000000000001',
              'span_id': '0000000000000002',
              'name': 'test',
              'annotations': [
                  {'type': 'timestamp', 'value': 1, 'key': 'cs'}]}])

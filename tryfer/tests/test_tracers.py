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

from unittest2 import TestCase

from tryfer.tracers import get_tracers, set_tracers, push_tracer
from tryfer.tracers import (
    EndAnnotationTracer,
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

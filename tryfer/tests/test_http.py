# Copyright 2012 Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from zope.interface.verify import verifyObject

from twisted.trial.unittest import TestCase

from twisted.web.resource import Resource, IResource
from twisted.web.server import Request
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from twisted.internet.defer import succeed

from tryfer.trace import Trace, Endpoint
from tryfer.http import TracingAgent, TracingWrapperResource


class TracingAgentTests(TestCase):
    def setUp(self):
        self.agent = mock.Mock(Agent)
        self.trace = mock.Mock(Trace)
        self.trace.trace_id = 1
        self.trace.span_id = 2
        self.trace.parent_span_id = 1

        child_trace = self.trace.child.return_value

        child_trace.trace_id = 1
        child_trace.span_id = 3
        child_trace.parent_span_id = 2

    @mock.patch('tryfer.http.Trace')
    def test_no_parent(self, mock_trace):
        mock_trace.return_value.trace_id = 1
        mock_trace.return_value.span_id = 2
        mock_trace.return_value.parent_span_id = 3

        agent = TracingAgent(self.agent)
        agent.request('GET', 'https://google.com')

        # Constructs a new trace object.
        mock_trace.assert_called_with('GET')

    def test_with_parent(self):
        agent = TracingAgent(self.agent, self.trace)

        agent.request('GET', 'https://google.com')

        self.trace.child.assert_called_with('GET')

    @mock.patch('tryfer.http.Annotation')
    def test_uri_annotation(self, mock_annotation):
        agent = TracingAgent(self.agent, self.trace)

        agent.request('GET', 'https://google.com')

        mock_annotation.string.assert_any_call(
            'http.uri', 'https://google.com')

        self.trace.child.return_value.record.assert_any_call(
            mock_annotation.string.return_value)

    @mock.patch('tryfer.http.Annotation')
    def test_client_send_annotation(self, mock_annotation):
        agent = TracingAgent(self.agent, self.trace)

        agent.request('GET', 'https://google.com')

        mock_annotation.client_send.assert_called_with()
        self.trace.child.return_value.record.assert_any_call(
            mock_annotation.client_send.return_value)

    @mock.patch('tryfer.http.Annotation')
    def test_client_recv_annotation(self, mock_annotation):
        self.agent.request.return_value = succeed(mock.Mock())
        agent = TracingAgent(self.agent, self.trace)

        agent.request('GET', 'https://google.com')

        mock_annotation.client_recv.assert_called_with()
        self.trace.child.return_value.record.assert_any_call(
            mock_annotation.client_recv.return_value)

    def test_delgates_to_agent(self):
        agent = TracingAgent(self.agent, self.trace)

        agent.request('GET', 'https://google.com')

        self.agent.request.assert_called_with(
            'GET', 'https://google.com',
            Headers({'X-B3-TraceId': ['0000000000000001'],
                     'X-B3-SpanId': ['0000000000000003'],
                     'X-B3-ParentSpanId': ['0000000000000002']}),
            None)

    @mock.patch('tryfer.http.Trace')
    def test_sets_endpoint(self, mock_trace):
        endpoint = Endpoint('127.0.0.1', 0, 'client')
        agent = TracingAgent(self.agent, endpoint=endpoint)

        agent.request('GET', 'https://google.com')
        mock_trace.return_value.set_endpoint.assert_called_with(endpoint)


class TracingWrapperResourceTests(TestCase):
    def setUp(self):
        self.wrapped = mock.Mock(Resource)
        self.resource = TracingWrapperResource(self.wrapped)

        self.request = mock.Mock(Request)
        self.request.method = 'GET'
        self.request.requestHeaders = mock.Mock(wraps=Headers({}))
        self.request.getHost.return_value.host = '127.0.0.1'
        self.request.getHost.return_value.port = 8080

    def test_verifyObject(self):
        verifyObject(IResource, self.resource)

    def test_putChildRaises(self):
        self.assertRaises(
            NotImplementedError, self.resource.putChild, 'foo', mock.Mock())

    def test_renderRaises(self):
        self.assertRaises(
            NotImplementedError, self.resource.render, mock.Mock())

    def test_getChildWithDefault_calls_wrapped(self):
        self.assertEqual(
            self.resource.getChildWithDefault('foo', self.request),
            self.wrapped.getChildWithDefault.return_value)

        self.wrapped.getChildWithDefault.assert_called_with(
            'foo', self.request)

    @mock.patch('tryfer.http.Trace')
    def test_constructsTrace(self, mock_trace):
        self.resource.getChildWithDefault('foo', self.request)

        mock_trace.assert_called_with('GET', None, None, None)

    @mock.patch('tryfer.http.Annotation')
    @mock.patch('tryfer.http.Trace')
    def test_server_recv_annotation(self, mock_trace, mock_annotation):
        self.resource.getChildWithDefault('foo', self.request)

        mock_annotation.server_recv.assert_called_with()
        mock_trace.return_value.record(
            mock_annotation.server_recv.return_value)

    @mock.patch('tryfer.http.Annotation')
    @mock.patch('tryfer.http.Trace')
    def test_server_send_annotation(self, mock_trace, mock_annotation):
        self.request.notifyFinish.return_value = succeed(None)

        self.resource.getChildWithDefault('foo', self.request)

        mock_annotation.server_send.assert_called_with()

    @mock.patch('tryfer.http.Trace')
    def test_uses_trace_headers(self, mock_trace):
        self.request.requestHeaders.setRawHeaders('X-B3-TraceId', ['a'])
        self.request.requestHeaders.setRawHeaders('X-B3-SpanId', ['b'])
        self.request.requestHeaders.setRawHeaders('X-B3-ParentSpanId', ['c'])

        self.resource.getChildWithDefault('foo', self.request)

        mock_trace.assert_called_with('GET', 10, 11, 12)

    @mock.patch('tryfer.http.Trace')
    def test_uses_trace_headers_no_parent(self, mock_trace):
        self.request.requestHeaders.setRawHeaders('X-B3-TraceId', ['a'])
        self.request.requestHeaders.setRawHeaders('X-B3-SpanId', ['b'])

        self.resource.getChildWithDefault('foo', self.request)

        mock_trace.assert_called_with('GET', 10, 11, None)

    @mock.patch('tryfer.http.Trace')
    def test_sets_endpoint(self, mock_trace):
        self.resource.getChildWithDefault('foo', self.request)

        set_endpoint = mock_trace.return_value.set_endpoint
        self.assertEqual(set_endpoint.call_count, 1)
        endpoint = set_endpoint.mock_calls[0][1][0]

        self.assertEqual(endpoint.ipv4, '127.0.0.1')
        self.assertEqual(endpoint.port, 8080)
        self.assertEqual(endpoint.service_name, 'http')

    @mock.patch('tryfer.http.Trace')
    def test_sets_endpoint_with_service_name(self, mock_trace):
        resource = TracingWrapperResource(
            self.wrapped, service_name='test-http')

        resource.getChildWithDefault('foo', self.request)

        set_endpoint = mock_trace.return_value.set_endpoint
        self.assertEqual(set_endpoint.call_count, 1)
        endpoint = set_endpoint.mock_calls[0][1][0]

        self.assertEqual(endpoint.ipv4, '127.0.0.1')
        self.assertEqual(endpoint.port, 8080)
        self.assertEqual(endpoint.service_name, 'test-http')

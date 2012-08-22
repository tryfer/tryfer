import mock

from twisted.trial.unittest import TestCase

from twisted.web.client import Agent
from twisted.internet.defer import succeed

from tryfer.trace import Trace
from tryfer.http import TracingAgent


class TracingAgentTests(TestCase):
    def setUp(self):
        self.agent = mock.Mock(Agent)
        self.trace = mock.Mock(Trace)

    @mock.patch('tryfer.http.Trace')
    def test_no_parent(self, mock_trace):
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

        mock_annotation.string.assert_any_call('http.uri', 'https://google.com')

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

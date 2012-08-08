from collections import defaultdict

from zope.interface import implements

from twisted.internet import reactor
from twisted.internet.defer import succeed

from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer

from tryfer.interfaces import ITracer
from tryfer._thrift.zipkinCore import constants
from tryfer.formatters import json_formatter, base64_thrift_formatter


class StringProducer(object):
    """
    Writes a pre-defined string into the body of a
    L{twisted.web.client.Request}.
    """
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class _EndAnnotationTracer(object):
    implements(ITracer)

    END_ANNOTATIONS = (constants.CLIENT_RECV, constants.SERVER_SEND)

    def __init__(self):
        self._annotations_for_trace = defaultdict(list)

    def send_trace(self, trace, annotations):
        raise NotImplementedError("Should be implemented by transport specific subclass")

    def record(self, trace, annotation):
        trace_key = (trace.trace_id, trace.span_id)
        self._annotations_for_trace[trace_key].append(annotation)

        if annotation.name in self.END_ANNOTATIONS:
            annotations = self._annotations_for_trace[trace_key]
            self._annotations_for_trace[trace_key] = []
            self.send_trace(trace, annotations)


class RESTKinTracer(_EndAnnotationTracer):
    def __init__(self, trace_url, auth_token=None):
        super(RESTKinTracer, self).__init__()

        self._agent = Agent(reactor)
        self._trace_url = trace_url
        self._auth_token = auth_token

    def send_trace(self, trace, annotations):
        json_out = json_formatter(trace, annotations)
        producer = StringProducer(json_out)
        headers = Headers({})

        if self._auth_token is not None:
            headers.addRawHeader('X-Auth-Token', self._auth_token)

        self._agent.request('POST', self._trace_url, headers, producer)


class ZipkinTracer(_EndAnnotationTracer):
    def __init__(self, scribe_client, category=None):
        super(ZipkinTracer, self).__init__()
        self._scribe = scribe_client
        self._category = category or 'zipkin'

    def send_trace(self, trace, annotations):
        thrift_out = base64_thrift_formatter(trace, annotations)
        self._scribe.log(self._category, [thrift_out])


class DebugTracer(object):
    implements(ITracer)

    def __init__(self, destination):
        self.destination = destination

    def record(self, trace, annotation):
        self.destination.write('---\n')
        self.destination.write(
            ('Adding annotation for trace: {0.trace_id}:'
             '{0.parent_span_id}:{0.span_id}:{0.name}\n').format(trace))
        self.destination.write('\t')
        self.destination.write(
            '{0.name} = {0.value}:{0.annotation_type}\n'.format(annotation))
        self.destination.flush()


_globalTracers = []


def set_tracers(tracers):
    global _globalTracers
    _globalTracers = tracers


def push_tracer(tracer):
    global _globalTracers
    _globalTracers.append(tracer)


def get_tracers():
    return _globalTracers

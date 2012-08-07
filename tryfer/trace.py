import math
import time
import random

from zope.interface import implements

from tryfer.interfaces import ITrace, IAnnotation, IEndpoint
from tryfer.tracers import get_tracer
from tryfer._thrift.zipkinCore import constants


def _uniq_id():
    return random.randint(0, math.pow(2, 31))


class Trace(object):
    implements(ITrace)

    def __init__(self, name, trace_id=None, span_id=None,
                 parent_span_id=None, tracer=None):
        self.name = name
        self.trace_id = trace_id or _uniq_id()
        self.span_id = span_id or _uniq_id()
        self.parent_span_id = parent_span_id
        self._tracer = tracer or get_tracer()
        self._endpoint = None

    def child(self, name):
        trace = self.__class__(
            name, trace_id=self.trace_id, parent_span_id=self.span_id)
        trace.set_endpoint(self._endpoint)

        return trace

    def record(self, annotation):
        if annotation.endpoint is None and self._endpoint is not None:
            annotation.endpoint = self._endpoint

        self._tracer.record(self, annotation)

    def set_endpoint(self, endpoint):
        self._endpoint = endpoint


class Endpoint(object):
    implements(IEndpoint)

    def __init__(self, ipv4, port, service_name):
        self.ipv4 = ipv4
        self.port = port
        self.service_name = service_name


class Annotation(object):
    implements(IAnnotation)

    def __init__(self, name, value, annotation_type, endpoint=None):
        self.name = name
        self.value = value
        self.annotation_type = annotation_type
        self.endpoint = endpoint

    @classmethod
    def timestamp(cls, name, timestamp=None):
        if timestamp is None:
            timestamp = math.trunc(time.time() * 1000 * 1000)

        return Annotation(name, timestamp, 'timestamp')

    @classmethod
    def client_send(cls, timestamp=None):
        return cls.timestamp(constants.CLIENT_SEND, timestamp)

    @classmethod
    def client_recv(cls, timestamp=None):
        return cls.timestamp(constants.CLIENT_RECV, timestamp)

    @classmethod
    def server_send(cls, timestamp=None):
        return cls.timestamp(constants.SERVER_SEND, timestamp)

    @classmethod
    def server_recv(cls, timestamp=None):
        return cls.timestamp(constants.SERVER_RECV, timestamp)

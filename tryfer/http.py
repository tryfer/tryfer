from zope.interface import implements

from twisted.web.http_headers import Headers
from twisted.web.resource import IResource

from tryfer.interfaces import ITrace
from tryfer.trace import Trace, Annotation


class TracingAgent(object):
    def __init__(self, agent, parent_trace=None):
        self._agent = agent
        self._parent_trace = parent_trace

    def request(self, method, url, headers=None, bodyProducer=None):
        if self._parent_trace is None:
            trace = Trace(method)
        else:
            trace = self._parent_trace.child(method)

        if headers is None:
            headers = Headers({})

        # These headers are based on the headers used by finagle's tracing
        # http Codec.  https://github.com/twitter/finagle/blob/master/finagle-http/src/main/scala/com/twitter/finagle/http/Codec.scala#L200
        #
        # Currently not implemented are X-B3-Sampled and X-B3-Flags
        # Tryfer's underlying Trace implementation has no notion of a Sampled
        # trace and I haven't figured out what flags are for.
        headers.setRawHeaders('X-B3-TraceId', [trace.trace_id])
        headers.setRawHeaders('X-B3-SpanId', [trace.span_id])

        if trace.parent_span_id is not None:
            headers.setRawHeaders('X-B3-ParentSpanId', [trace.parent_span_id])

        # Similar to the headers above we use the annotation 'http.uri' for
        # because that is the standard set forth in the finagle http Codec.
        trace.record(Annotation.string('http.uri', url))
        trace.record(Annotation.client_send())

        def _finished(resp):
            trace.record(Annotation.client_recv())
            return resp

        d = self._agent.request(method, url, headers, bodyProducer)
        d.addBoth(_finished)

        return d


class TracingWrapperResource(object):
    implements(IResource)

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def getChild(self, path, request):
        headers = request.requestHeaders

        trace = Trace(
            request.method,
            headers.getRawHeaders('X-B3-TraceId', [None])[0],
            headers.getRawHeaders('X-B3-SpanId', [None])[0],
            headers.getRawHeaders('X-B3-ParentSpanId', [None])[0])

        request.setComponent(ITrace, trace)

        trace.record(Annotation.server_recv())

        def _record_finish(_ignore):
            trace.record(Annotation.server_send())

        request.notifyFinish().addCallback(_record_finish)

        return self._wrapped.getChild(path, request)

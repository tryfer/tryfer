from twisted.web.http_headers import Headers

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

        headers.addRawHeader('X-B3-TraceId', trace.trace_id)
        headers.addRawHeader('X-B3-SpanId', trace.span_id)

        if trace.parent_span_id is not None:
            headers.addRawHeader('X-B3-ParentSpanId', trace.parent_span_id)

        trace.record('http.uri', Annotation.string(url))
        trace.record(Annotation.client_send())

        def _finished(resp):
            trace.record(Annotation.client_recv())
            return resp

        d = self._agent.request(method, url, headers, bodyProducer)
        d.addBoth(_finished)

        return d

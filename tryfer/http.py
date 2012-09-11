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

from zope.interface import implements

from twisted.web.http_headers import Headers
from twisted.web.resource import IResource

from tryfer.interfaces import ITrace
from tryfer.trace import Trace, Annotation, Endpoint
from tryfer.formatters import hex_str


class TracingAgent(object):
    """
    An L{Agent} wrapper which traces requests.
    """

    def __init__(self, agent, parent_trace=None, endpoint=None):
        """
        @param parent_trace: An L{ITrace} provider which will be used
            as the parent of all traces.

        @param endpoint: An L{IEndpoint} provider which will be set on
            on all traces.
        """
        self._agent = agent
        self._parent_trace = parent_trace
        self._endpoint = endpoint

    def request(self, method, uri, headers=None, bodyProducer=None):
        """
        Send a client request following HTTP redirects.

        @see: L{Agent.request}.
        """
        if self._parent_trace is None:
            trace = Trace(method)
        else:
            trace = self._parent_trace.child(method)

        if self._endpoint is not None:
            trace.set_endpoint(self._endpoint)

        if headers is None:
            headers = Headers({})

        # These headers are based on the headers used by finagle's tracing
        # http Codec.
        #
        # https://github.com/twitter/finagle/blob/master/finagle-http/
        #
        # Currently not implemented are X-B3-Sampled and X-B3-Flags
        # Tryfer's underlying Trace implementation has no notion of a Sampled
        # trace and I haven't figured out what flags are for.
        headers.setRawHeaders('X-B3-TraceId', [hex_str(trace.trace_id)])
        headers.setRawHeaders('X-B3-SpanId', [hex_str(trace.span_id)])

        if trace.parent_span_id is not None:
            headers.setRawHeaders('X-B3-ParentSpanId',
                                  [hex_str(trace.parent_span_id)])

        # Similar to the headers above we use the annotation 'http.uri' for
        # because that is the standard set forth in the finagle http Codec.
        trace.record(Annotation.string('http.uri', uri))
        trace.record(Annotation.client_send())

        def _finished(resp):
            # TODO: It may be advantageous here to return a wrapped response
            # whose deliverBody can wrap it's protocol and record when the
            # application has finished reading the contents.
            trace.record(Annotation.string(
                'http.responsecode',
                '{0} {1}'.format(resp.code, resp.phrase)))
            trace.record(Annotation.client_recv())
            return resp

        d = self._agent.request(method, uri, headers, bodyProducer)
        d.addBoth(_finished)

        return d


def int_or_none(val):
    if val is None:
        return None

    return int(val, 16)


class TracingWrapperResource(object):
    implements(IResource)

    isLeaf = False

    def __init__(self, wrapped, service_name=None):
        """
        @param wrapped: An L{IResource} provider that we'll delegate child
            lookup to.

        @param service_name: A C{str} name of the service to be used in the
            L{IEndpoint} for traces from this resource.  Default: 'http'
        """
        self._wrapped = wrapped
        self._service_name = service_name or 'http'

    def render(self, request):
        raise NotImplementedError(
            "TracingWrapperResource.render should never be called")

    def putChild(self, path, child):
        raise NotImplementedError(
            "TracingWrapperResource.putChild is not implemented because"
            "TracingWrapperResource does not support children.")

    def getChildWithDefault(self, path, request):
        headers = request.requestHeaders

        # Construct and endpoint from the requested host and port and the
        # passed service name.
        host = request.getHost()

        endpoint = Endpoint(host.host, host.port, self._service_name)

        # Construct the trace using the headers X-B3-* headers that the
        # TracingAgent will send.
        trace = Trace(
            request.method,
            int_or_none(headers.getRawHeaders('X-B3-TraceId', [None])[0]),
            int_or_none(headers.getRawHeaders('X-B3-SpanId', [None])[0]),
            int_or_none(headers.getRawHeaders('X-B3-ParentSpanId', [None])[0]))

        trace.set_endpoint(endpoint)

        # twisted.web.server.Request is a subclass of Componentized this
        # allows us to use ITrace(request) to get the trace and object (and
        # create children of this trace) in the wrapped resource.
        request.setComponent(ITrace, trace)

        trace.record(Annotation.server_recv())

        def _record_finish(_ignore):
            trace.record(Annotation.server_send())

        # notifyFinish returns a deferred that fires when the request is
        # finished this will allow us to record server_send regardless of if
        # the wrapped resource us using deferred rendering.
        request.notifyFinish().addCallback(_record_finish)

        return self._wrapped.getChildWithDefault(path, request)

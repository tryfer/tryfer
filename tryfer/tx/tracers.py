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

from StringIO import StringIO

from zope.interface import implements

from twisted.python import log
from twisted.internet import reactor
from twisted.web.client import FileBodyProducer
from twisted.web.http_headers import Headers

from tryfer.interfaces import ITracer
from tryfer.formatters import json_formatter, base64_thrift_formatter
from tryfer.tracers import EndAnnotationTracer


class RawZipkinTracer(object):
    """
    Send annotations to Zipkin as Base64 encoded Thrift objects over scribe.

    This implementation logs all annotations immediately and does not implement
    buffering of any sort.

    @param scribe_client: An L{scrivener.ScribeClient} instance.

    @param category: A C{str} to be used as the scribe category.
    """
    implements(ITracer)

    def __init__(self, scribe_client, category=None):
        self._scribe = scribe_client
        self._category = category or 'zipkin'

    def record(self, traces):
        d = self._scribe.log(
            self._category,
            [base64_thrift_formatter(trace, annotations)
             for (trace, annotations) in traces])

        d.addErrback(
            log.err,
            "Error sending trace to scribe category: {0}".format(
                self._category))


class ZipkinTracer(object):
    """
    Send annotations to Zipkin as Base64 Encoded thrift objects over scribe.

    This is equivalent to EndAnnotationTracer(
    BufferingTracer(RawZipkinTracer(scribe_client))).

    This implementation mostly exists for convenience.

    @param scribe_client: See L{RawZipkinTracer}

    @param category: See L{RawZipkinTracer}

    @param end_annotations: See L{EndAnnotationTracer}

    @param max_traces: See L{BufferingTracer}

    @param max_idle_time: See L{BufferingTracer}

    @param _reactor: See L{BufferingTracer}
    """
    implements(ITracer)

    def __init__(self, scribe_client, category=None, end_annotations=None,
                 max_traces=50, max_idle_time=10, _reactor=None):
        self._tracer = EndAnnotationTracer(
            BufferingTracer(
                RawZipkinTracer(scribe_client, category),
                max_traces=max_traces,
                max_idle_time=max_idle_time,
                _reactor=_reactor),
            end_annotations=end_annotations
        )

    def record(self, traces):
        return self._tracer.record(traces)


class RawRESTkinHTTPTracer(object):
    """
    Send annotations to RESTkin over HTTP as JSON objects.

    This implementation posts all traces immediately and does not implement
    buffering.

    @param agent: An L{twisted.web.client.Agent} like object.  Which should be
        used to POST the given traces to the specified L{trace_url}.

    @param trace_url: The URL to the RESTkin trace API endpoint as a C{str}.
    """
    implements(ITracer)

    def __init__(self, agent, trace_url):
        self._agent = agent
        self._trace_url = trace_url

    def record(self, traces):
        producer = FileBodyProducer(StringIO(json_formatter(traces)))

        d = self._agent.request('POST', self._trace_url, Headers({}), producer)
        d.addErrback(
            log.err,
            "Error sending trace to: {0}".format(self._trace_url))


class RESTkinHTTPTracer(object):
    """
    Send annotations to RESTkin over HTTP as JSON objects.

    This is equivalent to EndAnnotationTracer(
    BufferingTracer(RawZipkinTracer(scribe_client))).

    This implementation mostly exists for convenience.

    @param agent: See L{RawRESTkinHTTPTracer}

    @param trace_url: See L{RESTkinHTTPTracer}

    @param end_annotations: See L{EndAnnotationTracer}

    @param max_traces: See L{BufferingTracer}

    @param max_idle_time: See L{BufferingTracer}

    @param _reactor: See L{BufferingTracer}
    """
    implements(ITracer)

    def __init__(self, agent, trace_url, end_annotations=None,
                 max_traces=50, max_idle_time=10, _reactor=None):
        self._tracer = EndAnnotationTracer(
            BufferingTracer(
                RawRESTkinHTTPTracer(agent, trace_url),
                max_traces=max_traces,
                max_idle_time=max_idle_time,
                _reactor=_reactor),
            end_annotations=end_annotations
        )

    def record(self, traces):
        self._tracer.record(traces)


class RawRESTkinScribeTracer(object):
    """
    Send annotations to RESTkin as JSON objects over Scribe.

    This implement sends all traces immediately and does no buffering.

    @param scribe_client: The L{ScribeClient} to log JSON traces to.

    @param category: The scribe category as a C{str}
    """
    implements(ITracer)

    def __init__(self, scribe_client, category=None):
        self._scribe_client = scribe_client
        self._category = category or 'restkin'

    def record(self, traces):
        d = self._scribe_client.log(
            self._category,
            [json_formatter(traces)])
        d.addErrback(
            log.err,
            "Error sending trace to scribe category: {0}".format(
                self._category))


class RESTkinScribeTracer(object):
    """
    Send annotations to RESTkin as JSON objects over Scribe.

    This is equivalent to EndAnnotationTracer(
    BufferingTracer(RawRESTkinScribeTracer(scribe_client))).

    This implementation mostly exists for convenience.

    @param scribe_client: See L{RawRESTkinScribeTracer}

    @param category: See L{RawRESTkinScribeTracer}

    @param end_annotations: See L{EndAnnotationTracer}

    @param max_traces: See L{BufferingTracer}

    @param max_idle_time: See L{BufferingTracer}

    @param _reactor: See L{BufferingTracer}
    """
    implements(ITracer)

    def __init__(self, scribe_client, category=None, end_annotations=None,
                 max_traces=50, max_idle_time=10, _reactor=None):
        self._tracer = EndAnnotationTracer(
            BufferingTracer(
                RawRESTkinScribeTracer(scribe_client, category),
                max_traces=max_traces,
                max_idle_time=max_idle_time,
                _reactor=_reactor),
            end_annotations=end_annotations
        )

    def record(self, traces):
        return self._tracer.record(traces)


class BufferingTracer(object):
    """
    Buffer traces and defer recording until L{max_traces} have been received or
    L{max_idle_time} has elapsed since the last trace was recorded.

    When L{max_traces} is exceeded, all buffered traces will be flushed.
    This means that for a max_traces of 5 if 10 traces are received, all
    10 traces will be flushed to the next tracer.

    @param tracer: An L{ITracer} provider to record bufferred traces to.

    @param max_traces: C{int} of the number of traces to buffer before
        recording occurs.  Default 50.

    @param max_idle_time: C{int} of number of seconds since the last trace was
        received to send all bufferred traces.  Default 10.

    @param _reactor: An L{I_reactorTime} provider used to defer buffering to a
        future reactor iteration.
    """
    implements(ITracer)

    def __init__(self, tracer, max_traces=50, max_idle_time=10, _reactor=None):
        self._max_traces = max_traces
        self._max_idle_time = max_idle_time

        self._reactor = _reactor or reactor
        self._tracer = tracer
        self._buffer = []
        self._idle_dc = None
        self._flush_dc = None

    def _reset(self):
        if self._idle_dc and self._idle_dc.active():
            self._idle_dc.reset(self._max_idle_time)
        else:
            self._idle_dc = self._reactor.callLater(
                self._max_idle_time, self._flush)

    def _flush(self):
        if self._idle_dc and self._idle_dc.active():
            self._idle_dc.cancel()

        if self._flush_dc is not None:
            self._flush_dc = None

        flushable = self._buffer
        self._buffer = []

        if flushable:
            self._tracer.record(flushable)

    def record(self, traces):
        self._buffer.extend(traces)

        if len(self._buffer) >= self._max_traces:
            # The buffer is full, flush in the next _reactor iteration.  If
            # we have not already scheduled a flush to happen.
            if self._flush_dc is None:
                self._flush_dc = self._reactor.callLater(0, self._flush)

        else:
            # The buffer is not full, reset the idle timer to DelayedCall to
            # flush after 10 seconds.
            self._reset()

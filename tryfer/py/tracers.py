import time
import logging
import threading

import Queue

import requests

from zope.interface import implements

from tryfer.interfaces import ITracer
from tryfer.tracers import EndAnnotationTracer
from tryfer.formatters import base64_thrift_formatter, json_formatter


class RawZipkinTracer(object):
    """
    Send annotations to Zipkin as Base64 encoded Thrift objects over scribe.

    This implementation logs all annotations immediately and does not implement
    buffering of any sort.

    @param scribe_client: An L{tryfer.py.scribe_client.ScribeClient} instance.

    @param category: A C{str} to be used as the scribe category.
    """
    implements(ITracer)

    logger = logging.getLogger('tryfer.py.tracers.RawZipkinTracer')

    def __init__(self, scribe_client, category='zipkin'):
        self._scribe_client = scribe_client
        self._category = category

    def record(self, traces):
        try:
            self._scribe_client.log(
                self._category,
                [base64_thrift_formatter(trace, annotations)
                 for (trace, annotations) in traces])
        except Exception:
            self.logger.exception(
                "Error sending traces to scribe category: {0}".format(
                    self._category))


class ZipkinTracer(object):
    """
    Send annotations to Zipkin as Base64 Encoded thrift objects over scribe.

    This is equivalent to EndAnnotationTracer(
    ThreadedBufferingTracer(RawZipkinTracer(scribe_client))).

    This implementation mostly exists for convenience.

    @param scribe_client: See L{RawZipkinTracer}

    @param category: See L{RawZipkinTracer}

    @param end_annotations: See L{EndAnnotationTracer}

    @param max_traces: See L{ThreadedBufferingTracer}

    @param send_interval: See L{ThreadedBufferingTracer}
    """
    implements(ITracer)

    def __init__(self, scribe_client, category=None, end_annotations=None,
                 max_traces=50, send_interval=10):
        self._tracer = EndAnnotationTracer(
            ThreadedBufferingTracer(
                RawZipkinTracer(scribe_client, category),
                max_traces=max_traces,
                send_interval=send_interval),
            end_annotations=end_annotations
        )

    def record(self, traces):
        return self._tracer.record(traces)


class RawRESTkinScribeTracer(object):
    """
    Send annotations to RESTkin as JSON objects over Scribe.

    This implement sends all traces immediately and does no buffering.

    @param scribe_client: The L{ScribeClient} to log JSON traces to.

    @param category: The scribe category as a C{str}
    """
    implements(ITracer)

    logger = logging.getLogger('tryfer.py.tracers.RawRESTkinScribeTracer')

    def __init__(self, scribe_client, category=None):
        self._scribe_client = scribe_client
        self._category = category or 'restkin'

    def record(self, traces):
        try:
            self._scribe_client.log(
                self._category,
                [json_formatter(traces)])
        except Exception:
            self.logger.exception(
                "Error sending traces to scribe category: {0}".format(
                    self._category))


class RESTkinScribeTracer(object):
    """
    Send annotations to RESTkin as JSON objects over Scribe.

    This is equivalent to EndAnnotationTracer(
    ThreadedBufferingTracer(RawRESTkinScribeTracer(scribe_client))).

    This implementation mostly exists for convenience.

    @param scribe_client: See L{RawRESTkinScribeTracer}

    @param category: See L{RawRESTkinScribeTracer}

    @param end_annotations: See L{EndAnnotationTracer}

    @param max_traces: See L{ThreadedBufferingTracer}

    @param send_interval: See L{ThreadedBufferingTracer}
    """
    implements(ITracer)

    def __init__(self, scribe_client, category=None, end_annotations=None,
                 max_traces=50, send_interval=10, _reactor=None):
        self._tracer = EndAnnotationTracer(
            ThreadedBufferingTracer(
                RawRESTkinScribeTracer(scribe_client, category),
                max_traces=max_traces,
                send_interval=send_interval),
            end_annotations=end_annotations
        )

    def record(self, traces):
        return self._tracer.record(traces)


class RESTkinHTTPTracer(object):
    """
    Send annotations to RESTkin over HTTP as JSON objects.

    This is equivalent to EndAnnotationTracer(
    ThreadedBufferingTracer(RawZipkinTracer(scribe_client))).

    This implementation mostly exists for convenience.

    @param agent: See L{RawRESTkinHTTPTracer}

    @param trace_url: See L{RESTkinHTTPTracer}

    @param end_annotations: See L{EndAnnotationTracer}

    @param max_traces: See L{ThreadedBufferingTracer}

    @param send_interval: See L{ThreadedBufferingTracer}
    """
    implements(ITracer)

    def __init__(self, agent, trace_url, end_annotations=None,
                 max_traces=50, send_interval=10):
        self._tracer = EndAnnotationTracer(
            ThreadedBufferingTracer(
                RawRESTkinHTTPTracer(agent, trace_url),
                max_traces=max_traces,
                send_interval=send_interval),
            end_annotations=end_annotations
        )

    def record(self, traces):
        self._tracer.record(traces)


class RawRESTkinHTTPTracer(object):
    """
    Send annotations to RESTkin over HTTP as JSON objects.

    This implementation posts all traces immediately and does not implement
    buffering.

    @param trace_url: The URL to the RESTkin trace API endpoint as a C{str}.
    """
    implements(ITracer)

    logger = logging.getLogger('tryfer.py.tracers.RawRESTkinHTTPTracer')

    def __init__(self, trace_url):
        self._trace_url = trace_url

    def record(self, traces):
        try:
            requests.post(self._trace_url, json_formatter(traces))
        except Exception:
            self.logger.exception(
                "Error sending traces to {0}".format(self._trace_url))


class ThreadedBufferingTracer(object):
    """
    Buffer traces and defer recording until L{max_traces} have been received or
    L{send_interval} has elapsed since the last trace was recorded.

    When L{max_traces} is exceeded, all buffered traces will be flushed.
    This means that for a max_traces of 5 if 10 traces are received, all
    10 traces will be flushed to the next tracer.

    @param tracer: An L{ITracer} provider to record bufferred traces to.

    @param max_traces: C{int} of the number of traces to buffer before
        recording occurs.  Default 50.

    @param send_interval: C{int} of frequency to send traces in seconds.
        Default 10.
    """
    implements(ITracer)

    def __init__(self, tracer, max_traces=50, send_interval=10):
        self._max_traces = max_traces
        self._send_interval = send_interval

        self._tracer = tracer
        self._buffer = []
        self._buffer_lock = threading.RLock()

        self._flush_queue = Queue.Queue()
        self._flush_thread = threading.Thread(target=self._flush_loop)
        self._flush_thread.daemon = True
        self._flush_thread.start()

    def _flush_loop(self):
        while True:
            try:
                self._flush_queue.get(block=True, timeout=self._send_interval)
            except Queue.Empty:
                pass

            self._flush()

    def _flush(self):
        with self._buffer_lock:
            flushable = self._buffer
            self._buffer = []

        if flushable:
            self._tracer.record(flushable)

    def record(self, traces):
        with self._buffer_lock:
            self._buffer.extend(traces)

            if len(self._buffer) >= self._max_traces:
                # The buffer is full, flush.
                self._flush_queue.put(None)

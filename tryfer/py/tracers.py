import logging

import requests

from zope.interface import implements

from tryfer.interfaces import ITracer
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


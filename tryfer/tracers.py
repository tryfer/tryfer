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

import sys

import logging

from collections import defaultdict

from zope.interface import implements

from tryfer.interfaces import ITracer
from tryfer._thrift.zipkinCore import constants
from tryfer.formatters import json_formatter


class EndAnnotationTracer(object):
    """
    A tracer which collects all annotations for a trace until an one of several
    possible "end annotations" are seen.  An end annotation indicates that from
    the perspective of this tracer the trace is complete.

    @cvar DEFAULT_END_ANNOTATIONS: Default C{list} of end annotations.

    @param tracer: An L{ITracer} provider to delegate to once an end annotation
        is seen.

    @param end_annotations: A C{list} of annotation names as C{str} which will
        be used in place of L{DEFAULT_END_ANNOTATIONS} if specified.
    """
    implements(ITracer)

    DEFAULT_END_ANNOTATIONS = (constants.CLIENT_RECV, constants.SERVER_SEND)

    logger = logging.getLogger('tryfer.tracers.EndAnnotationTracer')

    def __init__(self, tracer, end_annotations=None):
        self._tracer = tracer
        self._end_annotations = end_annotations or self.DEFAULT_END_ANNOTATIONS
        self._annotations_for_trace = defaultdict(list)

    def record(self, traces):
        for (trace, annotations) in traces:
            trace_key = (trace.trace_id, trace.span_id)
            self._annotations_for_trace[trace_key].extend(annotations)

            for annotation in annotations:
                if annotation.name in self._end_annotations:
                    saved_annotations = self._annotations_for_trace[trace_key]

                    del self._annotations_for_trace[trace_key]

                    self.logger.debug(
                        "Sending trace: %s w/ %r", trace_key, annotations)
                    self._tracer.record([(trace, saved_annotations)])

                    break


class DebugTracer(object):
    """
    Send annotations immediately to a file-like destination in JSON format.

    All traces will be written immediately to the destination.

    @param destination: A file-like object to write JSON formatted traces to.
    """
    implements(ITracer)

    def __init__(self, destination=None):
        self.destination = destination or sys.stdout

    def record(self, traces):
        self.destination.write(json_formatter(traces, indent=2))
        self.destination.write('\n')
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

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

from zope.interface import Interface, Attribute


class ITracer(Interface):
    """
    An ITracer is responsible for collecting and delivering annotations and
    traces.

    Traces are expected to be delivered asynchronously and ITracer.record is
    not expected to wait until a Trace has been successfully delivered before
    returning to it's caller.  Given the asynchronous nature of trace delivery
    any errors which occur as a result of attempting to deliver a trace MUST be
    handled by the ITracer provider.
    """

    def record(traces):
        """
        Record one or more annotations.

        XXX: 'traces' isn't a very good name.

        @param traces: A C{list} of 2-element C{tuple} objects whose first
            element is an L{ITrace} provider whose second element is a C{list}
            of L{IAnnotation} providers.

        @returns C{None}
        """


class ITrace(Interface):
    """
    An ITrace provider encapsulates information about the current span of this
    trace and provides a mechanism for creating new child spans and recording
    annotations for this span.
    """

    trace_id = Attribute("64-bit integer identifying this trace.")
    span_id = Attribute("64-bit integer identifying this span.")
    parent_span_id = Attribute(
        "64-bit integer identifying this trace's parent span or None.")
    name = Attribute("A string describing this span.")

    def child(name):
        """
        Return an provider which is a child of this one.  A trace T1 can be
        said to be a child of trace T0 if: T0.trace_id == T1.trace_id and
        T0.span_id == T1.parent_span_id.

        @returns L{ITracITracee} provider
        """

    def record(*annotations):
        """
        Record one or more annotations for this trace.  This is the primary
        entry point for associating annotations with traces.  It will delegate
        actual recording to zero or more L{ITracer} providers.

        @param annotations: One or more L{IAnnotation} providers.

        @returns C{None}
        """


class IEndpoint(Interface):
    """
    An IEndpoint represents a source of annotations in a distributed system.

    An endpoint represents the place where an event represented by an
    annotation occurs.

    In a simple client/server RPC system both the client and server will record
    Annotations for the same trace & span but those annotations will have
    separate endpoints.  On the client the endpoint will represent the client
    service and on the server the endpoint will represent server service.
    """

    ipv4 = Attribute("Dotted decimal string IP Address of this Endpoint")
    port = Attribute("Integer port of this Endpoint")
    service_name = Attribute("Name of the service for this endpoint.")


class IAnnotation(Interface):
    """
    An annotation represents a piece of information attached to a trace.

    Most commonly this will be an event like:
     * Client send
     * Server receive
     * Server send
     * Client receive

    It may however also include non-event information such as the URI of
    an HTTP request being made, or the user id that initiated the action
    which caused the operations being traced to be performed.
    """

    name = Attribute("The name of this annotation.")
    value = Attribute("The value of this annotation.")
    annotation_type = Attribute(
        "A string describing the type of this annotation.")
    endpoint = Attribute(
        "An IEndpoint where this annotation was created or None.")

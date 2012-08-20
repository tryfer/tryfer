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
    An ITracer is responsible for collecting and delivering annotations and traces.
    """

    def record(self, trace, annotation):
        """
        Record an annotation for the specified trace.
        """


class ITrace(Interface):
    trace_id = Attribute("64-bit integer identifying this trace.")
    span_id = Attribute("64-bit integer identifying this span.")
    parent_span_id = Attribute("64-bit integer identifying this trace's parent span or None.")
    name = Attribute("A string describing this span.")

    def child(self, name):
        """
        Return an ITrace which is a child of this one.
        """

    def record(self, annotation):
        """
        Record an annotation for this trace.
        """


class IEndpoint(Interface):
    ip = Attribute("IP Address of this Endpoint")
    port = Attribute("Port of this Endpoint")
    service_name = Attribute("Name of the service for this endpoint.")


class IAnnotation(Interface):
    name = Attribute("The name of this annotation.")
    value = Attribute("The value of this annotation.")
    annotation_type = Attribute("A string describing the type of this annotation.")
    endpoint = Attribute("An IEndpoint where this annotation was created or None.")

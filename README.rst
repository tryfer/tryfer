tryfer: A Twisted Zipkin Tracer Library
=======================================

Zipkin_ is a Distributed Tracing system, tryfer is a Python/Twisted_ client
library for Zipkin.

It's design is heavily influenced by Finagle_'s tracing libraries.

HTTP Tracing
------------

Tryfer natively supports tracing of HTTP requests on both the client and the
server, and relates these requests by passing a series of HTTP headers along
with the request.

Client
~~~~~~

The client side of this conversation is the ``TracingAgent`` which uses
Twisted's composable HTTP/1.1 client architecture to record ``CLIENT_SEND`` and
``CLIENT_RECV`` annotations for your request.  In addition it'll record
the full requested URL as a string annotation named ``http.uri``.

Server
~~~~~~

On the server you can wrap the root resource of your application in a
``TracingWrapperResource`` and it will automatically record ``SERVER_RECV`` and
``SERVER_SEND`` annotations.  It also provides access to the trace via the
request argument, so you can record extra annotations.

::

    def render(self, request):
      trace = request.getComponent(ITrace)
      trace.record(Annotation.string('name', 'value'))


Headers
~~~~~~~

``TracingAgent`` and ``TracingWrapperResource`` support a subset of headers defined by Finagle_.

* ``X-B3-TraceId`` - hex encoded trace id.
* ``X-B3-SpanId`` - hex encoded span id.
* ``X-B3-ParentSpanId`` - hex encoded span id of parent span.

Examples
~~~~~~~~

In the ``examples/`` subdirectory you'll find two python scripts (one client and
one server) which demonstrate the usage and expected output.

Start by opening two terminals and going to the tryfer source directory.

In terminal #1 we can start the server using `twistd`::

    tryfer> twistd -n -y examples/tracing-server.tac
    2012-09-05 13:22:02-0700 [-] Log opened.
    2012-09-05 13:22:02-0700 [-] twistd 12.1.0 (/Users/dreid/.virtualenvs/tracing/bin/python 2.7.2) starting up.
    2012-09-05 13:22:02-0700 [-] reactor class: twisted.internet.selectreactor.SelectReactor.
    2012-09-05 13:22:02-0700 [-] Site starting on 8080
    2012-09-05 13:22:02-0700 [-] Starting factory <twisted.web.server.Site instance at 0x100e78680>

In terminal #2 we will run the client which will make a single HTTP request to
the server::

    tryfer> python examples/tracing-client.py
    [
      {
        "annotations": [
          {
            "type": "string",
            "value": "http://localhost:8080/README.rst",
            "key": "http.uri"
          },
          {
            "type": "timestamp",
            "value": 1346876525257644,
            "key": "cs"
          },
          {
            "type": "timestamp",
            "value": 1346876525270536,
            "key": "cr"
          }
        ],
        "trace_id": "00e5f721d19e25fa",
        "name": "GET",
        "span_id": "007fe79f2c63db97"
      }
    ]
    Received 200 response.


Here we see some output from the DebugTracer which simply prints all
annotations it's asked to trace to stdout in json format.  Here we've included
our first annotation which is the http.uri we are requesting.

Now in terminal #1 we should see the following::

    2012-09-05 13:22:05-0700 [HTTPChannel,0,127.0.0.1] 127.0.0.1 - - [05/Sep/2012:20:22:05 +0000] "GET /README.rst HTTP/1.1" 200 4829 "-" "-"
    2012-09-05 13:22:05-0700 [EndAnnotationTracer] Sending trace: (64729494289524218, 36001992872811415) w/ (<tryfer.trace.Annotation object at 0x100e7bb90>,)
    [
      {
        "annotations": [
          {
            "host": {
              "service_name": "tracing-server-example",
              "ipv4": "127.0.0.1",
              "port": 8080
            },
            "type": "timestamp",
            "value": 1346876525268525,
            "key": "sr"
          },
          {
            "host": {
              "service_name": "tracing-server-example",
              "ipv4": "127.0.0.1",
              "port": 8080
            },
            "type": "timestamp",
            "value": 1346876525270173,
            "key": "ss"
          }
        ],
        "trace_id": "00e5f721d19e25fa",
        "name": "GET",
        "span_id": "007fe79f2c63db97"
      }
    ]


License
-------
::

    Copyright (C) 2012 Rackspace Hosting, Inc

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.


.. _Zipkin: https://github.com/twitter/zipkin
.. _Twisted: http://twistedmatrix.com/
.. _Finagle: https://github.com/twitter/finagle/tree/master/finagle-zipkin

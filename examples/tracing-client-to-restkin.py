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

from __future__ import print_function

import sys

from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.python import log
from tryfer.tracers import push_tracer, EndAnnotationTracer, RESTkinHTTPTracer

from tryfer.http import TracingAgent


if __name__ == '__main__':
    # Set up twisted's logging.
    log.startLogging(sys.stdout)

    # Set up our RESTkinHTTPTracer to send JSON to a RESTkin instance
    # If you're not running RESTkin locally (defaults to 6956), change
    # the URL to https://trace.k1k.me/v1.0/22/trace .... and add authentication
    # with the python twisted keystone agent
    # https://github.com/racker/python-twisted-keystone-agent
    push_tracer(EndAnnotationTracer(
                    RESTkinHTTPTracer(Agent(reactor),
                                      'http://localhost:6956/v1.0/22/trace',
                                      max_idle_time=0)))

    def _do():
        # The Agent API is composable so we wrap an Agent in a TracingAgent
        # and every call to TracingAgent.request will result in a client_send,
        # client_receive, and http.uri annotations.
        a = TracingAgent(Agent(reactor))
        d = a.request('GET', 'http://google.com')

        # Print the response code when receive the response.
        d.addCallback(lambda r: print("Received {0} response.".format(r.code)))

        # stop the reactor.
        d.addBoth(lambda _: reactor.callLater(1, reactor.stop))

    reactor.callLater(1, _do)

    reactor.run()

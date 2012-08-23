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

from twisted.web.client import Agent, RedirectAgent

from tryfer.tracers import push_tracer, DebugTracer

from tryfer.http import TracingAgent


def _print_response(resp):
    print(resp.code, resp.headers)


def fetch(method, url):
    a = TracingAgent(RedirectAgent(Agent(reactor)))
    d = a.request(method, url)
    d.addCallback(_print_response)
    d.addErrback(print)
    return d


if __name__ == '__main__':
    push_tracer(DebugTracer(sys.stdout))

    def _do():
        d = fetch(sys.argv[1], sys.argv[2])
        d.addBoth(lambda _: reactor.stop())

    reactor.callWhenRunning(_do)

    reactor.run()

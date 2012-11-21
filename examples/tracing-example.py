from __future__ import print_function
import time

from tryfer.tracers import push_tracer
from tryfer.py.scribe_client import ScribeClient
from tryfer.py.tracers import RESTkinScribeTracer

from tryfer.trace import Trace, Annotation

push_tracer(
    RESTkinScribeTracer(ScribeClient('localhost', 1234)))


for x in xrange(0, 50):
    t = Trace('DO A THING {0}'.format(x))
    t.record(Annotation.client_send())

    time.sleep(5)

    t.record(Annotation.string('man', 'why you gotta'))
    t.record(Annotation.client_recv())

time.sleep(10)

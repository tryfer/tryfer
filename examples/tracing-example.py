from __future__ import print_function
import time

from tryfer.tracers import push_tracer, EndAnnotationTracer
from tryfer.py.tracers import RawRESTkinHTTPTracer

from tryfer.trace import Trace, Annotation

push_tracer(EndAnnotationTracer(RawRESTkinHTTPTracer("http://localhost:6956/v1.0/asfd/trace")))

t = Trace("DO A THING")
t.record(Annotation.client_send())

time.sleep(2)

t.record(Annotation.string("man", "why you gotta"))
t.record(Annotation.client_recv())

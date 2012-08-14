if __name__ == '__main__':
    import sys

    from twisted.internet import reactor
    from twisted.python import log

    from tryfer.tracers import push_tracer, RESTkinScribeTracer
    from tryfer.trace import Trace, Annotation, Endpoint

    from scrivener import ScribeClient
    from twisted.internet.endpoints import TCP4ClientEndpoint

    log.startLogging(sys.stdout)

    push_tracer(RESTkinScribeTracer(ScribeClient(
        TCP4ClientEndpoint(reactor, 'localhost', 1234))))

    webEndpoint = Endpoint('10.0.0.1', 80, 'demo-web')
    backendEndpoint = Endpoint('10.0.0.2', 81, 'demo-backend')
    cacheEndpoint = Endpoint('10.0.0.3', 82, 'demo-cache1')
    cacheEndpoint2 = Endpoint('10.0.0.4', 82, 'demo-cache2')
    cacheEndpoint3 = Endpoint('10.0.0.5', 82, 'demo-cache3')

    def whenRunning():
        t = Trace("getServers")
        print t.trace_id
        t.set_endpoint(webEndpoint)
        t.record(Annotation.client_send())
        a = Annotation.server_recv()
        a.endpoint = backendEndpoint
        t.record(a)
        t.record(Annotation.string('url', 'http://google.com'))
        t.record(Annotation.string('snowman', u'\N{SNOWMAN}'))

        # t2 = t.child("getServersFromCache")
        # t2.set_endpoint(backendEndpoint)
        # t2.record(Annotation.client_send())
        # a = Annotation.server_recv()
        # a.endpoint = cacheEndpoint
        # t2.record(a)
        # t3 = t2.child("checkCache1")
        # t3.set_endpoint(cacheEndpoint)
        # t3.record(Annotation.client_send())
        # t4 = t2.child("checkCache2")
        # t4.set_endpoint(cacheEndpoint2)
        # t4.record(Annotation.client_send())
        # t5 = t2.child("checkCache3")
        # t5.set_endpoint(cacheEndpoint3)
        # t5.record(Annotation.client_send())
        # t3.record(Annotation.client_recv())
        # t4.record(Annotation.client_recv())
        # t5.record(Annotation.client_recv())
        # a = Annotation.server_send()
        # a.endpoint = cacheEndpoint
        # t2.record(a)
        # t2.record(Annotation.client_recv())
        a = Annotation.server_send()
        a.endpoint = backendEndpoint

        t.record(a)
        t.record(Annotation.client_recv())

        t6 = t.child("putServersInCache")
        t6.record(Annotation.client_send())
        t6.record(Annotation.client_recv())

        reactor.callLater(1, reactor.stop)

    reactor.callWhenRunning(whenRunning)
    reactor.run()

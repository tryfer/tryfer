from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed, fail
from twisted.internet.protocol import Protocol
from twisted.internet.error import connectionLost, connectionDone
from twisted.web.client import FileBodyProducer
from cStringIO import StringIO

import json

KEYSTONE_AUTH_HEADER = Headers({"Content-type": "application/json"})
MAX_RETRIES = 3

class KeystoneAgent(object):
    def __init__(self, agent, auth_url, auth_cred):
        """
        @param agent:
        @param auth_url:
        @param auth_cred:   A dictionary in the form {"username": "username", "password": "password"}
        """
        self.agent = agent
        self.auth_url = auth_url
        self.auth_cred = auth_cred
        self.auth_token = None

    def request(self, method, uri, headers=None, bodyProducer=None):
        return self._request(method, uri, headers=headers, bodyProducer=bodyProducer)

    def _request(self, method, uri, headers=None, bodyProducer=None, depth=MAX_RETRIES):
        if depth == 0:
            return fail()

        def _handleResponse(response, method, uri, headers):
            if response.code == 401:
                #The auth token was not accepted, force an update to the auth token and recurse
                self.auth_token = None
                return self._request(method, uri, headers=headers, bodyProducer=bodyProducer, depth=depth-1)
            else:
                #The auth token was accepted, return the response
                return response

        def _makeRequest(auth_token):
            headers.addRawHeader("X-Auth-Token", auth_token)
            req = self.agent.request(method, uri, headers=headers, bodyProducer=bodyProducer)
            req.addCallback(_handleResponse)
            return req

        #Asynchronously get the auth token, and make the request using it
        d = Deferred(self._getAuthToken)
        d.addCallback(_makeRequest)

        return d


    def _getAuthRequestBody(self):
        return json.dumps({"auth": {"passwordCredentials": self.auth_cred}})

    def _getAuthToken(self):
        def _handleAuthResponse(response):
            response.deliverBody(KeystoneAuthProtocol(auth_token))

        if self.auth_token is None
            agent = Agent(reactor)
            auth_token = Deferred()
            d = agent.request("POST", self.auth_url, KEYSTONE_AUTH_HEADER, FileBodyProducer(StringIO(self._getAuthRequestBody())
            d.addCallback(_handleAuthResponse)
        else:
            return succeed(self.auth_token)

class KeystoneAuthProtocol(Protocol):
    def __init__(self):
        self.buffer = StringIO()
        self.token = None
        self.response_dict = None

    def dataReceived(self, data):
        self.buffer.write(data)

    def connectionLost(self, reason):
        if reason == connectionDone:
            try:
                self.response_dict = json.joads(self.buffer.getvalue())
            except ValueError as e:
                pass
        elif reason == connectionLost:
            pass

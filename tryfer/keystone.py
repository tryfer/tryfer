from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed, fail
from twisted.internet.protocol import Protocol
from twisted.internet.error import ConnectionLost, ConnectionDone, ConnectError
from twisted.web.client import FileBodyProducer
from twisted.web.http_headers import Headers
from cStringIO import StringIO
from Queue import Queue

import json

KEYSTONE_AUTH_HEADER = Headers({"Content-type": ["application/json"]})
MAX_RETRIES = 3

NOT_AUTHENTICATED = 1
AUTHENTICATING = 2
AUTHENTICATED = 3

DEBUG = False

class KeystoneAgent(object):
    """
    Forwards requests to a server, handling authentication (X-Auth-Token header) transparently.
    When a forwarded request is denied (due to an expired token, or some other reason), a new token
    is obtained using the authencation credentials.
    """

    def __init__(self, agent, auth_url, auth_cred):
        """
        @param agent:       Agent to use for making authenticated requests
        @param auth_url:    URL to use for authentication
        @param auth_cred:   A dictionary in the form {"username": "username", "password": "password"}
        """
        self.agent = agent
        self.auth_url = auth_url
        self.auth_cred = auth_cred
        self.tenant_id = None
        self.auth_token = None
        self.auth_token_expires = None
        self._state = NOT_AUTHENTICATED
        self._token_requests = Queue()

    def request(self, method, uri, headers=None, bodyProducer=None):
        if DEBUG:
            print "KeystoneAgent request ({method}): {uri}".format(method=method, uri=uri)

        return self._request(method, uri, headers=headers, bodyProducer=bodyProducer)

    def _request(self, method, uri, headers=None, bodyProducer=None, depth=0):

        if headers is None:
            headers = Headers()

        if DEBUG:
            print "KeystoneAgent _request depth {depth} ({method}): {uri}".format(method=method, uri=uri, depth=depth)

        if depth == MAX_RETRIES:
            return fail(ConnectError("Max retries exceeded"))

        def _handleResponse(response, method=method, uri=uri, headers=headers):
            if DEBUG:
                print "KeystoneAgent _handleResponse ({method}): {uri}".format(method=method, uri=uri, depth=depth)
            if response.code == 401:
                #The auth token was not accepted, force an update to the auth token and recurse
                self.auth_token = None
                self.auth_token_expires = None

                #We are no longer authenticated
                self._state = NOT_AUTHENTICATED

                return self._request(method, uri, headers=headers, bodyProducer=bodyProducer, depth=depth+1)
            else:
                #The auth token was accepted, return the response
                return response

        def _makeRequest(auth_token):
            if DEBUG:
                print "KeystoneAgent _makeRequest token {auth_token} ({method}): {uri}".format(method=method, uri=uri, auth_token=auth_token)

            headers.setRawHeaders("X-Auth-Token", [auth_token])
            print method, uri, headers, bodyProducer
            req = self.agent.request(method, uri, headers=headers, bodyProducer=bodyProducer)
            req.addCallback(_handleResponse)
            return req

        #Asynchronously get the auth token, then make the request using it
        d = self._getAuthToken()
        d.addCallback(_makeRequest)
        return d

    def _getAuthRequestBodyProducer(self):
        return FileBodyProducer(StringIO(json.dumps({"auth": {"passwordCredentials": self.auth_cred}})))

    def _getAuthToken(self):
        """
        Get an auth token to be included as an X-Auth-Token header.  If we have a valid token already,
        it is immediately returned.  If we do not have a valid token, then get a new token.  If we are
        currently in the process of getting a token, put this request into a queue to be handled when
        the token is received.
        """
        if DEBUG:
            print "KeystoneAgent _getAuthToken"

        def _handleAuthBody(body):
            if DEBUG:
                print "KeystoneAgent _handleAuthBody: {body}".format(body=body)

            try:
                body_parsed = json.loads(body)
                self.auth_token = body_parsed['access']['token']['id'].encode('ascii', 'replace')
                self.tenant_id = body_parsed['access']['token']['tenant']['id'].encode('ascii', 'replace')
                self.auth_token_expires = body_parsed['access']['token']['expires'].encode('ascii', 'replace')

                self._state = AUTHENTICATED

                if DEBUG:
                    print "KeystoneAgent _handleAuthBody: found token {token}".format(token= self.auth_token)

                # Callback all queued auth token requests
                while not self._token_requests.empty():
                    self._token_requests.get().callback(self.auth_token)

            except ValueError as e:
                if DEBUG:
                    print "KeystoneAgent _handleAuthBody: bad response {error}".format(error = e)

                # We received bad JSON
                return fail(e)

        def _handleAuthResponse(response):
            if DEBUG:
                print "KeystoneAgent _handleAuthResponse: {response}".format(response=response)

            if response.code == 200:
                body = Deferred()
                response.deliverBody(KeystoneAuthProtocol(body))
                body.addCallback(_handleAuthBody)
                return body
            else:
                return fail()
                #return Failure(#exc)

        if DEBUG:
            print "KeystoneAgent _getAuthToken: state is {state}".format(state=self._state)

        if self._state == AUTHENTICATED:
            # We are authenticated, immediatelly succeed with the current auth token
            print "KeystoneAgent _getAuthToken: succeed with {token}".format(token=self.auth_token)
            return succeed(self.auth_token)
        elif self._state == NOT_AUTHENTICATED or self._state == AUTHENTICATING:
            # We cannot satisfy the auth token request immediately, put it in a queue

            if DEBUG:
                print "KeystoneAgent _getAuthToken: defer, place in queue"

            auth_token_deferred = Deferred()
            self._token_requests.put(auth_token_deferred)

            if self._state == NOT_AUTHENTICATED:
                if DEBUG:
                    print "KeystoneAgent _getAuthToken: not authenticated, start authentication process"

                # We are not authenticated, and not in the process of authenticating.
                # Set our state to authenticating and begin the authentication process
                self._state = AUTHENTICATING

                d = self.agent.request('POST', self.auth_url, KEYSTONE_AUTH_HEADER, self._getAuthRequestBodyProducer())
                d.addCallback(_handleAuthResponse)

            return auth_token_deferred
        else:
            # Bad state, fail
            return fail(ValueError("Invalid state encountered"))

class KeystoneAuthProtocol(Protocol):
    """
    A protocol to aggregate chunked data as its received, and fire a callback
    with the aggregated data when the connection is closed.
    """

    def __init__(self, auth_body):
        """
        @param auth_body:   Deferred to fire when all data have been aggregated.
        """
        self.buffer = StringIO()
        self.auth_body = auth_body

    def dataReceived(self, data):
        self.buffer.write(data)

    def connectionLost(self, reason):
        self.auth_body.callback(self.buffer.getvalue())
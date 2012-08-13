import json

from cStringIO import StringIO
from Queue import Queue
from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed, fail
from twisted.internet.protocol import Protocol
from twisted.internet.error import ConnectionLost, ConnectionDone, ConnectError
from twisted.web.client import FileBodyProducer
from twisted.web.http_headers import Headers
from twisted.python import log


class KeystoneAgent(object):
    """
    Fetches and inserts X-Auth-Token and X-Tenant-Id headers into requests made using this agent.

    @cvar auth_headers: Dictionary in the form ("X-Tenant-Id": "id", "X-Auth-Token": "token")
                        containing current authentication header data.
    @cvar MAX_RETRIES:  Maximum number of connection attempts to make before failing.
    """
    MAX_RETRIES = 3

    NOT_AUTHENTICATED = 1
    AUTHENTICATING = 2
    AUTHENTICATED = 3

    def __init__(self, agent, auth_url, auth_cred):
        """
        @param agent:       Agent for use by this class
        @param auth_url:    URL to use for Keystone authentication
        @param auth_cred:   A tuple in the form ("username", "password")
        """
        self.agent = agent
        self.auth_url = auth_url
        self.auth_cred = auth_cred

        self.auth_headers = {"X-Auth-Token": None, "X-Tenant-Id": None}
        self.auth_token_expires = None

        self._state = self.NOT_AUTHENTICATED
        self._headers_requests = Queue()

    def msg(self, msg, **kwargs):
        log.msg(format=msg, system="KeystoneAgent", **kwargs)

    def request(self, method, uri, headers=None, bodyProducer=None):
        self.msg("request (%(method)s): %(uri)s", method=method, uri=uri)

        return self._request(method, uri, headers=headers, bodyProducer=bodyProducer)

    def _request(self, method, uri, headers=None, bodyProducer=None, depth=0):
        self.msg("_request depth %(depth)s (%(method)s): %(uri)s",
                 method=method, uri=uri, depth=depth)

        if headers is None:
            headers = Headers()

        if depth == self.MAX_RETRIES:
            return fail(AuthenticationError("Authentication headers rejected after max retries"))

        def _handleResponse(response, method=method, uri=uri, headers=headers):
            self.msg("_handleResponse (%(method)s): %(uri)s",
                     method=method, uri=uri, depth=depth)

            if response.code == 401:
                #The auth headers were not accepted, force an update and recurse
                self.auth_headers = {"X-Auth-Token": None, "X-Tenant-Id": None}
                self._state = self.NOT_AUTHENTICATED

                return self._request(method, uri, headers=headers, bodyProducer=bodyProducer, depth=depth+1)
            else:
                #The auth headers were accepted, return the response
                return response

        def _makeRequest(auth_headers):
            self.msg("_makeRequest  %(auth_headers)s (%(method)s): %(uri)s",
                     method=method, uri=uri, auth_headers=auth_headers)

            for header, value in auth_headers.items():
                headers.setRawHeaders(header, [value])

            req = self.agent.request(method, uri, headers=headers, bodyProducer=bodyProducer)
            req.addCallback(_handleResponse)
            return req

        #Asynchronously get the auth headers, then make the request using them
        d = self._getAuthHeaders()
        d.addCallback(_makeRequest)
        return d

    def _getAuthRequestBodyProducer(self):
        return FileBodyProducer(StringIO(json.dumps({"auth":
                                                     {"passwordCredentials":
                                                      {"username": self.auth_cred[0],
                                                       "password": self.auth_cred[1]}}})))

    def _getAuthHeaders(self):
        """
        Get authentication headers. If we have valid header data already, they immediately return it.
        If not, then get new authentication data.  If we are currently in the process of getting the
        header data, put this request into a queue to be handled when the data are received.

        @returns:   A deferred that will eventually be called back with the header data
        """
        def _handleAuthBody(body):
            self.msg("_handleAuthBody: %(body)s", body=body)

            try:
                body_parsed = json.loads(body)

                tenant_id = body_parsed['access']['token']['tenant']['id'].encode('ascii')
                auth_token = body_parsed['access']['token']['id'].encode('ascii')
                auth_token_expires = body_parsed['access']['token']['expires'].encode('ascii')

                self.auth_headers["X-Tenant-Id"] = tenant_id
                self.auth_headers["X-Auth-Token"] = auth_token
                self.auth_token_expires = auth_token_expires

                self._state = self.AUTHENTICATED

                self.msg("_handleAuthHeaders: found token %(token)s, tenant id %(tenant_id)s",
                         token=self.auth_headers["X-Auth-Token"], tenant_id=self.auth_headers["X-Tenant-Id"])

                # Callback all queued auth headers requests
                while not self._headers_requests.empty():
                    self._headers_requests.get().callback(self.auth_headers)

            except ValueError as e:
                # We received a bad response
                return fail(MalformedJSONError("Malformed keystone response received"))

        def _handleAuthResponse(response):
            if response.code == 200:
                self.msg("_handleAuthResponse: %(response)s accepted", response=response)
                body = Deferred()
                response.deliverBody(StringIOReceiver(body))
                body.addCallback(_handleAuthBody)
                return body
            else:
                self.msg("_handleAuthResponse: %(response)s rejected", response=response)
                return fail(KeystoneAuthenticationError("Keystone authentication credentials rejected"))

        self.msg("_getAuthHeaders: state is %(state)s", state=self._state)

        if self._state == self.AUTHENTICATED:
            # We are authenticated, immediately succeed with the current auth headers
            self.msg("_getAuthHeaders: succeed with %(headers)s", headers=self.auth_headers)

            return succeed(self.auth_headers)
        elif self._state == self.NOT_AUTHENTICATED or self._state == self.AUTHENTICATING:
            # We cannot satisfy the auth header request immediately, put it in a queue
            self.msg("_getAuthHeaders: defer, place in queue")
            auth_headers_deferred = Deferred()
            self._headers_requests.put(auth_headers_deferred)

            if self._state == self.NOT_AUTHENTICATED:
                self.msg("_getAuthHeaders: not authenticated, start authentication process")
                # We are not authenticated, and not in the process of authenticating.
                # Set our state to authenticating and begin the authentication process
                self._state = self.AUTHENTICATING

                d = self.agent.request('POST', self.auth_url,
                                       Headers({"Content-type": ["application/json"]}),
                                       self._getAuthRequestBodyProducer())
                d.addCallback(_handleAuthResponse)

            return auth_headers_deferred
        else:
            # Bad state, fail

            return fail(RuntimeError("Invalid state encountered"))


class AuthenticationError(Exception):
    pass


class KeystoneAuthenticationError(AuthenticationError):
    pass


class MalformedJSONError(Exception):
    pass


class StringIOReceiver(Protocol):
    """
    A protocol to aggregate chunked data as its received, and fire a callback
    with the aggregated data when the connection is closed.
    """

    def __init__(self, finished):
        """
        @param body:   Deferred to fire when all data have been aggregated.
        """
        self.buffer = StringIO()
        self.finished = finished

    def dataReceived(self, data):
        self.buffer.write(data)

    def connectionLost(self, reason):
        self.finished.callback(self.buffer.getvalue())

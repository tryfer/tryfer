import mock

import unittest2 as unittest

from thrift import Thrift

from tryfer._thrift.scribe.scribe import LogEntry

from tryfer.py.scribe_client import ScribeClient


class ScribeClientTests(unittest.TestCase):
    @mock.patch('tryfer.py.scribe_client.threading.Lock')
    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TSocket.TSocket')
    def test_log_locks(self, TSocket, Client, Lock):
        sc = ScribeClient('127.0.0.1', '1234')

        sc.log('foo', ['bar'])

        Lock.return_value.acquire.assert_called_once_with()
        Lock.return_value.release.assert_called_once_with()

    @mock.patch('tryfer.py.scribe_client.threading.Lock')
    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TSocket.TSocket')
    def test_log_release_lock_on_thrift_exception(self, TSocket, Client, Lock):
        sc = ScribeClient('127.0.0.1', '1234')

        Client.return_value.Log.side_effect = Thrift.TException()

        sc.log('foo', ['bar'])

        Lock.return_value.release.assert_called_once_with()

    @mock.patch('tryfer.py.scribe_client.threading.Lock')
    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TSocket.TSocket')
    def test_log_release_lock_and_propogates_exceptions(
            self, TSocket, Client, Lock):
        sc = ScribeClient('127.0.0.1', '1234')

        Client.return_value.Log.side_effect = ValueError("test exception")

        self.assertRaises(ValueError, sc.log, 'foo', ['bar'])

        Lock.return_value.release.assert_called_once_with()

    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TSocket.TSocket')
    def test_log_calls_Log_with_LogEntries(self, TSocket, Client):
        sc = ScribeClient('127.0.0.1', '1234')

        sc.log('foo', ['bar', 'baz'])

        Client.return_value.Log.assert_called_with([
            LogEntry('foo', 'bar'),
            LogEntry('foo', 'baz')
        ])

    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TTransport.TFramedTransport')
    def test_log_opens_closed_transport(self, TFramedTransport, Client):
        sc = ScribeClient('127.0.0.1', '1234')

        TFramedTransport.return_value.isOpen.return_value = False

        sc.log('foo', ['bar'])

        TFramedTransport.return_value.isOpen.assert_called_once_with()
        TFramedTransport.return_value.open.assert_called_once_with()

    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TTransport.TFramedTransport')
    def test_log_doesnt_open_open_transport(self, TFramedTransport, Client):
        sc = ScribeClient('127.0.0.1', '1234')

        TFramedTransport.return_value.isOpen.return_value = True

        sc.log('foo', ['bar'])

        TFramedTransport.return_value.isOpen.assert_called_once_with()
        self.assertEqual(TFramedTransport.return_value.open.call_count, 0)

    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TTransport.TFramedTransport')
    def test_log_exception_closes_transport(self, TFramedTransport, Client):
        sc = ScribeClient('127.0.0.1', '1234')

        TFramedTransport.return_value.isOpen.return_value = True

        Client.return_value.Log.side_effect = ValueError("test exception")

        self.assertRaises(ValueError, sc.log, 'foo', ['bar'])

        TFramedTransport.return_value.close.assert_called_once_with()

    @mock.patch('tryfer.py.scribe_client.Client')
    @mock.patch('tryfer.py.scribe_client.TTransport.TFramedTransport')
    def test_log_thrift_exception_closes_transport(
            self, TFramedTransport, Client):
        sc = ScribeClient('127.0.0.1', '1234')

        TFramedTransport.return_value.isOpen.return_value = True

        Client.return_value.Log.side_effect = Thrift.TException()

        sc.log('foo', ['bar'])

        TFramedTransport.return_value.close.assert_called_once_with()

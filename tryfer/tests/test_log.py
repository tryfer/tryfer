import mock

from twisted.trial.unittest import TestCase

from tryfer import log
from twisted.python import log as twisted_log


class LogTests(TestCase):
    def setUp(self):
        self.mock_log_patcher = mock.patch('tryfer.log.log')
        self.mock_log = self.mock_log_patcher.start()

    def tearDown(self):
        log.set_debugging(False)
        self.mock_log_patcher.stop()

    def test_default_debug_off(self):
        log.debug('test')
        self.assertEqual(self.mock_log.msg.call_count, 0)

    def test_set_debugging_default(self):
        log.set_debugging()
        log.debug('test')
        self.mock_log.msg.assert_called_once_with('test', logLevel='DEBUG')

    def test_set_debugging_explicit(self):
        log.set_debugging(True)
        log.debug('test')
        self.mock_log.msg.assert_called_once_with('test', logLevel='DEBUG')

    def test_set_debugging_off(self):
        log.set_debugging(True)
        log.debug('test')

        log.set_debugging(False)
        log.debug('test2')
        self.mock_log.msg.assert_called_once_with('test', logLevel='DEBUG')

    # log.msg and log.err don't call the twisted log functions, they
    # are simply references to them.
    def test_msg(self):
        self.assertEqual(log.msg, twisted_log.msg)

    def test_err(self):
        self.assertEqual(log.err, twisted_log.err)

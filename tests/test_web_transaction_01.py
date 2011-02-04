import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

class WebTransactionTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_inactive(self):
        self.assertEqual(_newrelic.transaction(), None)

    def test_transaction(self):
        environ = { "REQUEST_URI": "/test_transaction" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertEqual(_newrelic.transaction(), transaction)
            time.sleep(1.0)

    def test_custom_parameters(self):
        environ = { "REQUEST_URI": "/custom_parameters" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            transaction.custom_parameters["1"] = "1" 
            transaction.custom_parameters["2"] = "2" 
            transaction.custom_parameters["3"] = 3
            transaction.custom_parameters["4"] = 4.0
            transaction.custom_parameters["5"] = ("5", 5)
            transaction.custom_parameters["6"] = ["6", 6]
            transaction.custom_parameters["7"] = {"7": 7}
            transaction.custom_parameters[8] = "8"
            transaction.custom_parameters[9.0] = "9.0"
            time.sleep(1.0)

    def test_explicit_runtime_error(self):
        environ = { "REQUEST_URI": "/explicit_runtime_error" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            for i in range(10):
                try:
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.runtime_error(*sys.exc_info())

    def test_implicit_runtime_error(self):
        environ = { "REQUEST_URI": "/implicit_runtime_error" }
        transaction = _newrelic.WebTransaction(application, environ)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/application_disabled" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            self.assertEqual(_newrelic.transaction(), transaction)
        application.enabled = True

if __name__ == '__main__':
    unittest.main()

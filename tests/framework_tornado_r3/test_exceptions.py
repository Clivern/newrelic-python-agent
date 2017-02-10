import sys
import tornado
import threading

import pytest

from newrelic.packages import six

from tornado_base_test import TornadoBaseTest, TornadoZmqBaseTest

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty,
    tornado_validate_unscoped_metrics)

from _test_async_application import (AsyncLateExceptionRequestHandler,
        CoroutineLateExceptionRequestHandler,
        OutsideTransactionErrorRequestHandler,
        ScheduleAndCancelExceptionRequestHandler,
        SyncLateExceptionRequestHandler, ExceptionInsteadOfFinishHandler)

INTERNAL_SERVER_ERROR = 'Internal Server Error'

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

class AllTests(object):

    # Tests for exceptions occuring inside of a transaction.

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:ZeroDivisionError',
            py3='builtins:ZeroDivisionError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncExceptionRequestHandler.get')
    def test_sync_exception(self):
        response = self.fetch_exception('/sync-exception')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.reason, INTERNAL_SERVER_ERROR)

    scoped_metrics = [('Function/_test_async_application:'
            'CallbackExceptionRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'CallbackExceptionRequestHandler.counter_callback', 5)]

    @tornado_validate_errors(errors=[select_python_version(
            py2='exceptions:NameError', py3='builtins:NameError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallbackExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_callback_exception(self):
        response = self.fetch_exception('/callback-exception')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.reason, INTERNAL_SERVER_ERROR)

    scoped_metrics = [
            ('Function/_test_async_application:'
            'CoroutineExceptionRequestHandler.get', 1),
            (select_python_version(
                py2='Function/_test_async_application:get (coroutine)',
                py3='Function/_test_async_application:'
                    'CoroutineExceptionRequestHandler.get (coroutine)'),
             1),
            ('Function/_test_async_application:'
            'CoroutineExceptionRequestHandler._inc', 1),]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_coroutine_exception_0(self):
        response = self.fetch_exception('/coroutine-exception/0')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.reason, INTERNAL_SERVER_ERROR)

    scoped_metrics = [('Function/_test_async_application:'
            'CoroutineExceptionRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'CoroutineExceptionRequestHandler._inc', 1),]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_coroutine_exception_1(self):
        response = self.fetch_exception('/coroutine-exception/1')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.reason, INTERNAL_SERVER_ERROR)

    scoped_metrics = [
            # The get request handler is double counted. See PYTHON-1967.
            # ('Function/_test_async_application:'
            #  'CoroutineException2RequestHandler.get', 1),
            (select_python_version(
                py2='Function/_test_async_application:get (coroutine)',
                py3='Function/_test_async_application:'
                    'CoroutineException2RequestHandler.get (coroutine)'), 1),
            ('Function/_test_async_application:'
            'CoroutineException2RequestHandler._inc', 1),]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineException2RequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_coroutine_exception_2(self):
        response = self.fetch_exception('/coroutine-exception-2')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.reason, INTERNAL_SERVER_ERROR)

    scoped_metrics = [
           # The request handler is double counted. See PYTHON-1967.
           #('Function/_test_async_application:'
           # 'CallbackFromCoroutineRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'CallbackFromCoroutineRequestHandler.error', 1),]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallbackFromCoroutineRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_callback_from_coroutine_exception(self):
        response = self.fetch_exception('/callback-from-coroutine')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.reason, INTERNAL_SERVER_ERROR)

    scoped_metrics = [('Function/_test_async_application:'
            'SyncLateExceptionRequestHandler.get', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:SyncLateExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_sync_late_exception(self):
        response = self.fetch_response('/sync-late-exception')
        # Exception occurs after response comes back
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                SyncLateExceptionRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'AsyncLateExceptionRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'AsyncLateExceptionRequestHandler.done', 1),
            ('Function/_test_async_application:'
            'AsyncLateExceptionRequestHandler.error', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:AsyncLateExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_async_late_exception(self):
        response = self.fetch_response('/async-late-exception')
        # Exception occurs after response comes back
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                AsyncLateExceptionRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'CoroutineLateExceptionRequestHandler.get', 1),
            (select_python_version(
                py2='Function/_test_async_application:get (coroutine)',
                py3='Function/_test_async_application:'
                    'CoroutineLateExceptionRequestHandler.get (coroutine)'), 1),
            ('Function/_test_async_application:'
            'CoroutineLateExceptionRequestHandler.resolve_future', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[
            '_test_async_application:Tornado4TestException'])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CoroutineLateExceptionRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_coroutine_late_exception(self):
        response = self.fetch_response('/coroutine-late-exception')
        # Exception occurs after response comes back
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                CoroutineLateExceptionRequestHandler.RESPONSE)

    scoped_metrics = [('Function/_test_async_application:'
            'ScheduleAndCancelExceptionRequestHandler.get', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:ScheduleAndCancelExceptionRequestHandler'
            '.get',
            scoped_metrics=scoped_metrics,
            forgone_metric_substrings=['do_error'])
    def test_schedule_and_cancel_exception(self):
        response = self.fetch_response('/almost-error')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                ScheduleAndCancelExceptionRequestHandler.RESPONSE)

    # Tests for exceptions happening outside of a transaction

    def after_divide(self):
        self.stop()

    def divide_by_zero(self):
        quotient = 0
        try:
            quotient = 5/0
        finally:
            self.io_loop.add_callback(self.after_divide)
        return quotient

    def schedule_divide_by_zero(self):
        self.io_loop.add_callback(self.divide_by_zero)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[], expect_transaction=False,
            app_exceptions=[select_python_version(
                    py2='exceptions:ZeroDivisionError',
                    py3='builtins:ZeroDivisionError')])
    def test_stack_context_no_transaction_exception(self):
        # This tests that we record exceptions when they are not in a
        # transaction, but they do occur within a stack context. That is they
        # are scheduled asynchronously in a way where one wants to keep track of
        # the stack context, such as via a context manager. Just as a note,
        # it is possible for code written by an application developer to occur
        # within an ExceptionStackContext implicitly, request handlers do this
        # for example.

        # The lambda here is an exception handler which swallows the exception.
        with tornado.stack_context.ExceptionStackContext(
                lambda type, value, traceback: True):
            self.schedule_divide_by_zero()
        self.wait(timeout=5.0)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[], expect_transaction=False,
            app_exceptions=[select_python_version(
                    py2='exceptions:ZeroDivisionError',
                    py3='builtins:ZeroDivisionError')])
    def test_threaded_no_transaction_exception(self):
        # This tests that we record exceptions when an error occurs outside a
        # transaction and outside a stack context. This can be done when a job
        # is scheduled from another thread or is initiated outside of an
        # ExceptionStackContext context manager. By default, tests are run
        # inside an ExceptionStackContext so we spawn a new thread for this
        # test.
        t = threading.Thread(target=self.schedule_divide_by_zero)
        t.start()
        t.join(5.0)
        self.wait(timeout=5.0)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[],
            app_exceptions=[select_python_version(
                py2='exceptions:ZeroDivisionError',
                py3='builtins:ZeroDivisionError')])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OutsideTransactionErrorRequestHandler.get')
    @tornado_validate_unscoped_metrics([('Errors/all', 1)])
    def test_outside_transaction_exception(self):
        self.waits_expected += 1
        OutsideTransactionErrorRequestHandler.set_cleanup(
            self.waits_counter_check)

        response = self.fetch_response('/outside-transaction-error')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body,
                OutsideTransactionErrorRequestHandler.RESPONSE)

    scoped_metrics = [
            ('Function/_test_async_application:'
                    'ExceptionInsteadOfFinishHandler.get', 1),
    ]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:ExceptionInsteadOfFinishHandler.get',
            scoped_metrics=scoped_metrics)
    def test_exception_before_finish_in_callback(self):
        response = self.fetch_exception('/exception-instead-of-finish')
        self.assertEqual(response.code, 500)
        self.assertEqual(response.reason, INTERNAL_SERVER_ERROR)

class ExceptionDefaultIOLoopTest(AllTests, TornadoBaseTest):
    pass

@pytest.mark.skipif(sys.version_info < (2, 7),
        reason='pyzmq does not support Python 2.6')
class ExceptionZmqIOLoopTest(AllTests, TornadoZmqBaseTest):
    pass

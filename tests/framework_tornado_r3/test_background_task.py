import sys

import pytest

import tornado.gen

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace

from tornado_base_test import TornadoBaseTest, TornadoZmqBaseTest

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty)


# Define functions and background tasks at the module level, so
# that names are consistent (and simple!) for both python 2 and 3.
# Originally, I defined functions inside the test methods, and
# callable_name() in python 3 would return names like this:
#
#   ('test_background_task:TornadoTest.'
#    'test_background_task_finalize_in_callback.'
#    '<locals>.do_background_task')

@function_trace()
def do_stuff():
    pass

@function_trace()
def yield_stuff():
    raise tornado.gen.Return('yielded stuff')

class ExceptionAfterTransactionRecorded(Exception): pass

@function_trace()
def do_error():
    raise ExceptionAfterTransactionRecorded()

@background_task()
def do_nothing_background_task():
    pass

@background_task()
def do_stuff_background_task():
    do_stuff()

@background_task()
def add_callback_background_task(io_loop, func, *args, **kwargs):
    io_loop.add_callback(func, *args, **kwargs)

@background_task()
@tornado.gen.coroutine
def coroutine_background_task():
    do_stuff()
    yield yield_stuff()

@background_task()
@tornado.gen.coroutine
def schedule_and_cancel_callback_task(io_loop):
    timeout = io_loop.call_later(1.0, do_error)
    io_loop.remove_timeout(timeout)
    do_stuff()

@background_task()
@tornado.gen.coroutine
def spawn_callback_background_task(io_loop):
    io_loop.spawn_callback(do_stuff)
    do_stuff()


# Actual tests start here!

class AllTests(object):

    scoped_metrics = [('Function/test_background_task:do_stuff', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            'test_background_task:do_stuff_background_task',
            background_task=True,
            scoped_metrics=scoped_metrics)
    def test_background_task_do_stuff_synchronous(self):
        self.waits_expected += 1
        do_stuff_background_task()
        self.wait(timeout=5.0)

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            'test_background_task:do_stuff_background_task',
            background_task=True,
            scoped_metrics=scoped_metrics)
    def test_background_task_do_stuff_as_callback(self):
        self.waits_expected += 1
        self.io_loop.add_callback(do_stuff_background_task)
        self.wait(timeout=5.0)

    scoped_metrics = [('Function/test_background_task:do_stuff', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            'test_background_task:add_callback_background_task',
            background_task=True,
            scoped_metrics=scoped_metrics)
    def test_background_task_finalize_in_callback(self):
        self.waits_expected += 1
        add_callback_background_task(self.io_loop, do_stuff)
        self.wait(timeout=5.0)

    scoped_metrics = [('Function/test_background_task:do_error', 1)]
    errors = ['test_background_task:ExceptionAfterTransactionRecorded']

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=errors)
    @tornado_validate_count_transaction_metrics(
            'test_background_task:add_callback_background_task',
            background_task=True,
            scoped_metrics=scoped_metrics)
    def test_background_task_finalize_in_callback_error(self):
        self.waits_expected += 1
        add_callback_background_task(self.io_loop, do_error)
        try:
            self.wait(timeout=5.0)
        except ExceptionAfterTransactionRecorded:
            pass

    scoped_metrics = [
            ('Function/test_background_task:do_stuff', 1),
            ('Function/test_background_task:yield_stuff', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            'test_background_task:coroutine_background_task',
            background_task=True,
            scoped_metrics=scoped_metrics)
    def test_background_task_coroutine(self):
        self.waits_expected += 1
        coroutine_background_task()
        self.wait(timeout=5.0)

    scoped_metrics = [('Function/test_background_task:do_stuff', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            'test_background_task:schedule_and_cancel_callback_task',
            background_task=True,
            scoped_metrics=scoped_metrics,
            forgone_metric_substrings=['do_error'])
    def test_background_task_schedule_cancel_callback(self):
        self.waits_expected += 1
        schedule_and_cancel_callback_task(self.io_loop)
        self.wait(timeout=5.0)

    scoped_metrics = [('Function/test_background_task:do_stuff', 2)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            'test_background_task:spawn_callback_background_task',
            background_task=True,
            scoped_metrics=scoped_metrics)
    def test_background_task_spawn_callback(self):
        self.waits_expected += 1
        spawn_callback_background_task(self.io_loop)
        self.wait(timeout=5.0)

class TornadoDefaultIOLoopTest(AllTests, TornadoBaseTest):
    pass

@pytest.mark.skipif(sys.version_info < (2, 7),
        reason='pyzmq does not support Python 2.6')
class TornadoZmqTest(AllTests, TornadoZmqBaseTest):
    pass

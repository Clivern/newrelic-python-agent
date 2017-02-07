import sys

import pytest

import tornado.gen
import tornado.testing
import tornado.web
if sys.version_info >= (2, 7):
    from zmq.eventloop.ioloop import ZMQIOLoop

from tornado.websocket import websocket_connect, WebSocketHandler

from tornado_fixtures import (tornado_validate_transaction_cache_empty,
        tornado_validate_errors)

from testing_support.fixtures import function_not_called


class BaseWebSocketsHandler(WebSocketHandler):

    def initialize(self, close_future):
        self.close_future = close_future

    def on_close(self):
        self.close_future.set_result((self.close_code, self.close_reason))


class BaseWebSocketsTest(tornado.testing.AsyncHTTPTestCase):

    def get_protocol(self):
        return 'ws'

    @tornado.gen.coroutine
    def ws_connect(self, url):
        ws = yield websocket_connect(url)
        raise tornado.gen.Return(ws)

    @tornado.gen.coroutine
    def close(self, ws):
        ws.close()
        yield self.close_future

class BaseWebSocketsZmqTest(BaseWebSocketsTest):
    def get_new_ioloop(self):
        return ZMQIOLoop()


class HelloHandler(BaseWebSocketsHandler):

    def on_message(self, message):
        self.write_message(b'hello', binary=True)


class AllTests(object):

    def get_app(self):
        self.close_future = tornado.gen.Future()
        return tornado.web.Application([
            ('/', HelloHandler, {'close_future': self.close_future}),
        ])

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(expect_transaction=False)
    @function_not_called('newrelic.api.transaction', 'Transaction.__init__')
    @tornado.testing.gen_test
    def test_no_transaction_no_errors(self):
        url = self.get_url('/')
        ws = yield self.ws_connect(url)
        result = ws.write_message('foo')

        # For Tornado >= 4.3, result is a future.
        if result:
            yield result

        response = yield ws.read_message()
        self.assertEqual(response, b'hello')

        yield self.close(ws)

class TornadoWebSocketsDefaultIOLoopTest(AllTests, BaseWebSocketsTest):
    pass

@pytest.mark.skipif(sys.version_info < (2, 7),
        reason='pyzmq does not support Python 2.6')
class TornadoWebSocketsZmqIOLoopTest(AllTests, BaseWebSocketsZmqTest):
    pass

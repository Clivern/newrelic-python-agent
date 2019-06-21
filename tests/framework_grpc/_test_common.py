import grpc
import threading
import functools
from newrelic.api.application import application_instance


def create_stub(port):
    return create_stub_and_channel(port)[0]


def create_stub_and_channel(port):
    from sample_application.sample_application_pb2_grpc import (
            SampleApplicationStub)
    channel = grpc.insecure_channel('localhost:%s' % port)
    stub = SampleApplicationStub(channel)
    return stub, channel


def create_request(streaming_request, count=1, timesout=False):
    from sample_application.sample_application_pb2 import Message

    def _message_stream():
        for i in range(count):
            yield Message(text='Hello World', count=count, timesout=timesout)

    if streaming_request:
        request = _message_stream()
    else:
        request = Message(text='Hello World', count=count, timesout=timesout)

    return request


def get_result(method, request, *args, **kwargs):
    from grpc._channel import _Rendezvous
    result = None
    try:
        result = method(request, *args, **kwargs)
        list(result)
    except _Rendezvous as e:
        result = e
    except Exception:
        pass
    return result


def wait_for_transaction_completion(fn):
    CALLED = threading.Event()
    application = application_instance()
    record_transaction = application.record_transaction

    def record_transaction_wrapper(*args, **kwargs):
        record_transaction(*args, **kwargs)
        CALLED.set()

    @functools.wraps(fn)
    def _waiter(*args, **kwargs):
        application.record_transaction = record_transaction_wrapper
        try:
            result = fn(*args, **kwargs)
            CALLED.wait(timeout=1)
            return result
        finally:
            application.record_transaction = record_transaction

    return _waiter
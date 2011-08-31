import sys
import types

import newrelic.api.transaction
import newrelic.api.object_wrapper
import newrelic.api.external_trace

class capture_external_trace(object):
    def __init__(self, wrapped):
        self._nr_next_object = wrapped
    def __call__(self, url):
        if url.split(':')[0].lower() in ['http', 'https', 'ftp']:
            current_transaction = newrelic.api.transaction.transaction()
            if current_transaction:
                trace = newrelic.api.external_trace.ExternalTrace(
                        current_transaction, 'feedparser', url)
                context_manager = trace.__enter__()
                try:
                    result = self._nr_next_object(url)
                except:
                    context_manager.__exit__(*sys.exc_info())
                    raise
                context_manager.__exit__(None, None, None)
                return result
            else:
                return self._nr_next_object(url)
        else:
            return self._nr_next_object(url)
    def __getattr__(self, name):
       return getattr(self._nr_next_object, name)

def instrument(module):
    newrelic.api.object_wrapper.wrap_object(
            module, 'parse', capture_external_trace)

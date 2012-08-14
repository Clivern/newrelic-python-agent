import unittest
import types

import newrelic.api.object_wrapper

_function_args = None

def _function(*args, **kwargs):
    return (args, kwargs)

class _wrapper(object):
   def __init__(self, wrapped):
       self.wrapped = wrapped
   def __get__(self, obj, objtype=None):
       return types.MethodType(self, obj, objtype)
   def __call__(self, *args, **kwargs):
       global _function_args
       _function_args = (args, kwargs)
       return self.wrapped(*args, **kwargs)

class ApplicationTests(unittest.TestCase):

    def test_wrap_object(self):
        newrelic.api.object_wrapper.wrap_object(
                __name__, '_function', _wrapper)
        args = (1, 2, 3)
        kwargs = { "one": 1, "two": 2, "three": 3 }
        result = _function(*args, **kwargs)
        self.assertEqual(result, (args, kwargs))

if __name__ == '__main__':
    unittest.main()
try:
    from urllib2 import urlopen  # Py2.X
except ImportError:
    from urllib.request import urlopen   # Py3.X

import sqlite3 as db

from newrelic.api.transaction import (add_user_attribute, add_custom_parameter,
        record_exception, get_browser_timing_header, get_browser_timing_footer,
        record_custom_event)
from newrelic.api.web_transaction import wsgi_application

_custom_parameters = {
        'user' : 'user-name',
        'account' : 'account-name',
        'product' : 'product-name',
        'bytes' : b'bytes-value',
        'string' : 'string-value',
        'unicode' : u'unicode-value',
        'integer' : 1,
        'float' : 1.0,
        'invalid-utf8' : b'\xe2',
        'multibyte-utf8' : b'\xe2\x88\x9a',
        'multibyte-unicode' : b'\xe2\x88\x9a'.decode('utf-8'),
        'list' : [],
        'tuple' : (),
        'dict' : {},
}

_err_param = {
        'err-param' : 'value'
}

def user_attributes_added():
    """Expected values when the custom parameters in this file are added as user
    attributes
    """
    user_attributes = _custom_parameters.copy()
    user_attributes['list'] = '[]'
    user_attributes['tuple'] = '()'
    user_attributes['dict'] = '{}'
    return user_attributes

def error_user_params_added():
    return _err_param.copy()

@wsgi_application()
def fully_featured_app(environ, start_response):
    status = '200 OK'

    path = environ.get('PATH_INFO')
    use_user_attrs = environ.get('record_attributes', 'TRUE') == 'TRUE'

    if use_user_attrs:

        # The add_user_attribute() call is now just an alias for
        # calling add_custom_parameter() but for backward compatibility
        # still need to check it works.

        for attr, val in _custom_parameters.items():
            if attr in ['user', 'product', 'account']:
                add_user_attribute(attr, val)
            else:
                add_custom_parameter(attr, val)

    if 'db' in environ and int(environ['db']) > 0:
        connection = db.connect(":memory:")
        for i in range(int(environ['db']) - 1):
            connection.execute("create table test_db%d (a, b, c)" % i)

    if 'external' in environ:
        for i in range(int(environ['external'])):
            r = urlopen('http://www.python.org')
            r.read(10)

    if 'err_message' in environ:
        n_errors = int(environ.get('n_errors', 1))
        for i in range(n_errors):
            try:

                # append number to stats engine to get unique errors, so they
                # don't immediately get filtered out.

                raise ValueError(environ['err_message'] + str(i))
            except ValueError:
                if use_user_attrs:
                    record_exception(params=_err_param)
                else:
                    record_exception()

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

@wsgi_application()
def simple_exceptional_app(environ, start_response):

    start_response('500 :(',[])

    raise ValueError('Transaction had bad value')

@wsgi_application()
def simple_app(environ, start_response):
    status = '200 OK'

    start_response(status, response_headers=[])

    return []

@wsgi_application()
def simple_custom_event_app(environ, start_response):

    params = {'snowman': u'\u2603', 'foo': 'bar'}
    record_custom_event('SimpleAppEvent', params)

    start_response(status='200 OK', response_headers=[])
    return []

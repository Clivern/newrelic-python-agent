import webtest

import cherrypy

class Resource(object):

    exposed = True

    def GET(self):
        return 'GET RESPONSE'

dispatcher = cherrypy.dispatch.MethodDispatcher()

conf = { '/': { 'request.dispatch': dispatcher } }

application = cherrypy.Application(Resource(), '/', conf)
test_application = webtest.TestApp(application)

def test_resource_get():
    response = test_application.get('')
    response.mustcontain('GET RESPONSE')

def test_resource_not_found():
    response = test_application.post('', status=405)
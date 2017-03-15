
class BuilderMiddleware(object):
    def __init__(self, app, builder):
        self.app = app
        self.builder = builder

    def __call__(self, environ, start_response):
        self.builder.build_if_needed()
        return self.app(environ, start_response)
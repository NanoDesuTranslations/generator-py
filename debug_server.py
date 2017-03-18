import tornado.ioloop
import tornado.web
from fs.errors import FileExpected, ResourceNotFound

def start_debug_server(debug_fs, port=8000, special=None):
    if special is None:
        special = {}
    class DebugHandler(tornado.web.RequestHandler):
        def get(self):
            print(self.request.uri)
            uri = self.request.uri
            
            special_f = special.get(uri)
            if special_f:
                self.finish(str(special_f()))
                return
            
            if uri == '/':
                self.finish(debug_fs.open("/index.html").read())
                return
            try:
                if uri.endswith('.css'):
                    self.set_header('Content-Type', 'text/css')
                self.finish(debug_fs.open(uri).read())
            except FileExpected:
                if not uri.endswith('/'):
                    self.redirect('{}/'.format(uri), True)
                    return
                self.finish(debug_fs.open(uri + "/index.html").read())
            except ResourceNotFound:
                self.set_status(404)
                self.finish()
            
    
    app = tornado.web.Application([
        (r"/.*", DebugHandler),
    ], debug=True)
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()

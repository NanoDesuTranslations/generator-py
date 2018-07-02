import tornado.ioloop
import tornado.web
from fs.errors import FileExpected, ResourceNotFound

def start_single_page_server(debug_fs, single_page_cb, port=8000, special=None, debug=False):
    if special is None:
        special = {}
    class DebugHandler(tornado.web.RequestHandler):
        def get(self):
            # print(self.request.uri)
            uri = self.request.uri
            
            special_f = special.get(uri)
            if special_f:
                self.finish(str(special_f()))
                return
            
            if uri.startswith('/p/'):
                page_id = uri.split('/')[2]
                # print("SINGLE PAGE CALL", uri, page_id)
                data = single_page_cb(page_id)
                self.finish(data)
                return
            if uri.startswith('/pi/'):
                page_id = uri.split('/')[2]
                # print("SINGLE PAGE CALL", uri, page_id)
                data = single_page_cb(page_id, inner_only=True)
                self.finish(data)
                return
            
            if uri == '/':
                self.finish(debug_fs.open("/index.html").read())  
                return
            try:
                if uri.endswith('.css'):
                    self.set_header('Content-Type', 'text/css')
                if uri.endswith('.jpg'):
                    self.set_header('Content-Type', 'image/jpg')
                #self.finish(debug_fs.open(uri).read())
                self.finish(debug_fs.getbytes(uri))
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
    ], debug=debug)
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()

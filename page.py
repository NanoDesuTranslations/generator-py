from ordering import page_sort_key_predicate
from util import try_int

class Page:
    def __init__(self, page=None, series=None, root=None, parent=None):
        self.children = {}
        if root is None:
            self.root = self
        else:
            self.root = root
        self.parent = parent
        self.series = series
        self.config = series.config
        self.path = []
        self.path_part = None
        self.user_path = None
        self.is_index = True
        self.order = None
        self.renderer = None
        
        self.title = ''
        self.nav_title = None
        if page is not None:
            self.set_raw_page(page)
    
    def add_page(self, path, page):
        if path == []:
            self.set_raw_page(page)
            return
        cur = self
        cur_path = []
        for p in path:
            cur_path.append(p)
            if p in cur.children:
                cur = cur.children[p]
            else:
                new_page = Page(root=self.root, series=self.series, parent=cur)
                new_page.path = list(cur_path)
                new_page.path_part = p
                cur.children[p] = new_page
                cur = new_page
        
        cur.set_raw_page(page)
    
    def get_title(self):
        if self.nav_title is not None:
            return self.nav_title
        if self.title:
            title = self.title
            
            if title.startswith("{}: ".format(self.path_part)):
                return title
            if title.endswith(" {}".format(self.path_part)):
                return title
            
            if try_int(self.path_part, None) is not None:
                title = "{}: {}".format(self.path_part, title)
            return title
        elif self.user_path:
            return self.user_path.title()
        else:
            title = "{} {}".format(self.get_index_title(), self.path_part)
            return title
    
    def get_index_title(self):
        path_i = len(self.path)
        try:
            title = self.series.hier[path_i-1]
            return title.title()
        except IndexError:
            return '-'
    
    def set_raw_page(self, page):
        meta = page.get('meta', {})
        
        self.content = str(page['content'])
        self.title = str(meta.get('title', ''))
        self.renderer = str(meta.get('renderer_t', 'markdown'))
        self.is_index = False
        self.user_path = str(meta.get('path'))
        self.nav_title = str(meta.get('nav_title') or '') or None
        
        order = meta.get('order', 0)
        if order == "_0":
            order = 0
        self.order = try_int(order, order) or 0
    
    def get_path(self):
        return self.path
    
    def get_fs_series_path(self):
        url_prefix = self.config.path_prefix
        series_prefix = self.config.series_prefix
        
        if series_prefix:
            path = '/{}'.format(self.series.path_part)
        else:
            path = ''
        if url_prefix:
            path = url_prefix + path
        
        return path or '/'
    
    def get_fs_path(self):
        url_prefix = self.config.path_prefix
        series_prefix = self.config.series_prefix
        
        if series_prefix:
            path = '/{}'.format(self.series.path_part)
        else:
            path = ''
        if url_prefix:
            path = url_prefix + path
        parts = []
        cur = self
        while cur.parent is not None:
            parts.append(cur.path_part)
            cur = cur.parent
        parts = [str(p) for p in parts]
        return path + "/" + "/".join(reversed(parts)) + "/"
    
    def tree(self, depth=0, front=""):
        print(" "*depth, front, self.title if not self.is_index else "_", sep="")
        for p_n, c in sorted(self.children.items()):
            c.tree(depth+1, "{} ".format(p_n))
    
    def recurse(self):
        yield self
        for c in self:
            yield from c.recurse()
    
    def build_fs(self, out_fs):
        with out_fs.open('index.html', 'w') as f:
            f.write(self.render())
        
        if not self.is_index and self.config['include-raw']:
            content = self.content
            with out_fs.open('raw.md', 'w') as f:
                f.write(content)
            out_fs.makedir('raw', recreate=True)
            with out_fs.open('raw/index.html', 'w') as f:
                f.write("<pre>" + content + "</pre>")
        
        for child in self:
            p_n = str(child.path_part)
            out_fs.makedir(p_n, recreate=True)
            child.build_fs(out_fs.opendir(p_n))
    
    def render(self):
        return self.config.page_renderer.render(self)
    
    def __getitem__(self, key):
        return self.children[key]
    
    def __iter__(self):
        for child in sorted((c[1] for c in self.children.items()), key=page_sort_key_predicate):
            yield child

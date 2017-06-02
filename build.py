"""

python build.py

"""

from pprint import pprint
import sys

from fs.osfs import OSFS
from fs.ftpfs import FTPFS
from fs import open_fs
import fs
import fs.path
import pymongo
import hjson

from page import Page
import blog

from util import try_int
from render import PageRenderer

class ConfigError(Exception):
    pass

class Config:
    def __init__(self, additional_file=None):
        self.additional_file = additional_file
        self.load_config()
        
        self.page_renderer = PageRenderer(self)
    
    def load_config(self, config_override=None):
        if config_override is None:
            with open('config/default.hjson', encoding='utf8') as f:
                raw_config = hjson.loads(f.read())
                try:
                    with open('config/local.hjson', encoding='utf8') as f:
                        raw_config.update(hjson.loads(f.read()))
                except FileNotFoundError:
                    pass
                if self.additional_file:
                    try:
                        with open('config/{}.hjson'.format(self.additional_file), encoding='utf8') as f:
                            raw_config.update(hjson.loads(f.read()))
                    except FileNotFoundError:
                        pass
        else:
            raw_config = config_override
        
        self.raw_config = raw_config
        self.url_prefix = raw_config['url-prefix'] or ""
        self.env_url_prefix = raw_config['env-url-prefix'] or ""
        if self.url_prefix and self.env_url_prefix:
            raise ConfigError()
        self.path_prefix = self.url_prefix or self.env_url_prefix
        self.series_prefix = bool(raw_config['series_preifx'])
    
    def get(self, key, default=None):
        return self.raw_config.get(key, default)
    
    def __getitem__(self, key):
        return self.raw_config[key]

class Series:
    def __init__(self, raw_series, config):
        self.config = config
        
        self.raw_series = raw_series
        
        s_config = raw_series.get('config', {})
        self.name = raw_series['name']
        self.header_url = s_config.get('header-url', '')
        self.hier = s_config.get('hierarchy', [])
        self.id = str(raw_series['_id'])
        self.path_part = self.name.lower().replace(' ', '-')
        self.fixed_nav_entries = bool(s_config.get('fixed_nav_entries', True))

def retrieve_pages(config):
    remote = pymongo.MongoClient(config['mongo-url'])
    series_query = {}
    if config.get('series'):
        series_query['name'] = {'$in': config.get('series')}
    if config['min-status'] is not None:
        series_query['config.status'] = {'$gte': config['min-status']}
    remote_series = remote.ndtest.series.find(series_query)
    remote_series = list(remote_series)
    series_ids = [str(s['_id']) for s in remote_series]
    page_query = {
        'series': {'$in': series_ids}, 
    }
    if config['min-status'] is not None:
        page_query['meta.status'] = {'$gte': config['min-status']}
    remote_pages = remote.ndtest.pages.find(page_query)
    remote_pages = list(remote_pages)

    blog_pages = [p for p in remote_pages if p['meta'].get('blog')]
    blog_pages = [p for p in blog_pages if not p['meta'].get('deleted')]

    remote_pages = [p for p in remote_pages if not p['meta'].get('deleted')]
    remote_pages = [p for p in remote_pages if not p['meta'].get('blog')]
    
    all_pages = {}

    for raw_series in remote_series:
        series = Series(raw_series, config)
        
        hier = series.hier
        series_id = series.id
        pages = [p for p in remote_pages if p['series'] == series_id]
        series_blog_pages = [p for p in blog_pages if p['series'] == series_id]
        
        root = Page(series=series)
        all_pages[series.name] = root
        
        for page in pages:
            path = [page.get('meta', {}).get(h) for h in hier]
            path = [p for p in path if p not in [None, '', 0]]
            path = [0 if p == '_0' else p for p in path]
            path = [try_int(p, p) for p in path]
            
            path_postfix = page['meta'].get('path')
            if path_postfix:
                path.append(path_postfix)
            
            root.add_page(path, page)
            
            for path, page in blog.process_blog_posts(series_blog_pages, series):
                if path == []:
                    for child in root:
                        child.change_root(page)
                    page.children = root.children
                    root = page
                    all_pages[series.name] = root
                else:
                    root.add_page_obj(path, page)
    
    return all_pages

def gen_fs(test_fs, all_pages, config, include_static=True, noisy=False):
    if include_static:
        test_fs.removetree('/')
    else:
        for d in test_fs.listdir('/'):
            if d == 'static':
                continue
            if test_fs.isfile(d):
                test_fs.remove(d)
            else:
                test_fs.removetree(d)
    
    for name, root in all_pages.items():
        if config.series_prefix:
            test_fs.makedir(root.series.path_part)
            root.build_fs(test_fs.opendir(root.series.path_part))
        else:
            root.build_fs(test_fs)
    
    #generate an index page of series if multi series site
    if config.series_prefix:
        with test_fs.open('index.html', 'w') as f:
            f.write('<a style="color:black" href="https://nanodesutranslations.wordpress.com/"><h1>Nanodesu</h1></a>')
            for name, root in all_pages.items():
                series = root.series
                f.write('<div><a href="{}">{}</a><br></div>'.format(series.path_part, series.name))
    
    if include_static:
        with open_fs("osfs://static") as static_fs:
            fs.copy.copy_fs(static_fs, test_fs)

def main():
    try:
        config_fn_i = sys.argv.index('--config')
        config_fn = sys.argv[config_fn_i + 1]
    except (ValueError, IndexError):
        config = Config()
    else:
        config = Config(config_fn)
    
    all_pages = retrieve_pages(config)
    
    ftp_info = config.get('ftp-info')
    if ftp_info is not None:
        include_static = 'static' in sys.argv
        
        ftp_uri = "{host}".format(**ftp_info)
        
        class SpecialFTPFS(FTPFS):
            def makedir(self, path, recreate=False, *args, **kwargs):
                try:
                    return FTPFS.makedir(self, path, *args, **kwargs)
                except fs.errors.DirectoryExists:
                    pass
        
        with SpecialFTPFS(ftp_uri, user=ftp_info['user'], passwd=ftp_info['pass']) as ftp_fs:
            if config.url_prefix:
                ftp_fs.makedir(config.url_prefix)
                ftp_fs = ftp_fs.opendir(config.url_prefix)
            gen_fs(ftp_fs, all_pages, config, include_static=include_static, noisy=True)
    else:
        debug_mode = "debug" in sys.argv
        
        def get_out_fs():
            if debug_mode:
                return open_fs("mem://")
            else:
                osfs_url = "osfs://{}".format(config['output-path'])
                return open_fs(osfs_url, create=True)
        
        with get_out_fs() as out_fs:
            out_fs_root = out_fs
            if config.url_prefix:
                out_fs.makedir(config.url_prefix, recreate=True)
                out_fs = out_fs.opendir(config.url_prefix)
            
                gen_fs(out_fs, all_pages, config)
            else:
                gen_fs(out_fs, all_pages, config)
            
            if "tree" in sys.argv:
                out_fs_root.tree()
            
            if debug_mode:
                import debug_server
                def regen():
                    config.load_config()
                    config.page_renderer.load_templates()
                    gen_fs(out_fs, all_pages, config)
                    if "tree" in sys.argv:
                        out_fs_root.tree()
                def p_reload():
                    config.load_config()
                    config.page_renderer.load_templates()
                    all_pages = retrieve_pages(config)
                    gen_fs(out_fs, all_pages, config)
                
                special_pages = {'/regen': regen, '/reload': p_reload}
                debug_server.start_debug_server(out_fs_root, config['debug-server-port'], special_pages)

if __name__ == '__main__':
    main()

"""

python build.py

start a debug server on part 8888
python build.py debug

run single page server
python build.py --page _

run single page server in debug mode
python build.py --page debug

"""

from pprint import pprint
import sys
from itertools import groupby
import hashlib

from fs.osfs import OSFS
from fs.ftpfs import FTPFS
from fs import open_fs
import fs
import fs.path
import pymongo
import hjson
from redis import Redis
from pymongo import MongoClient

from page import Page
import blog

from util import try_int
from render import PageRenderer
from render.prerender import PreRenderer
from assets import ImageSrc
import build_target.fs_target, build_target.debug_target, build_target.netlify_target

class ConfigError(Exception):
    pass

class State:
    def __init__(self, config):
        self._config = config
        self.config = config
        self.series = None
        self.pages = None
        self.other = {}
        self.partial_build = False
        
        self._mongo_connection: MongoClient = None
        self._redis_connection: Redis = None
    
    def get_mongo(self):
        if self._mongo_connection is not None:
            return self._mongo_connection
        self._mongo_connection = MongoClient(self._config['mongo-url'])
        return self._mongo_connection
    
    def get_redis(self):
        if not self._config['redis-url']:
            return None
        if self._redis_connection is not None:
            return self._redis_connection
        self._redis_connection = Redis(host=self._config['redis-url'])
        return self._redis_connection
    
    def close(self):
        if self._mongo_connection:
            self._mongo_connection.close()
            self._mongo_connection = None
        if self._redis_connection:
            self._redis_connection.connection_pool.disconnect()
            self._redis_connection = None

class Config:
    def __init__(self, additional_file=None):
        self.additional_file = additional_file
        self.load_config()
        
        self.page_renderer = None
    
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
        
        image_server = raw_config.get('image_server', {})
        self.image_server = image_server.get('host')
        self.image_server_auth = image_server.get('auth')
    
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
        self.uuid = str(raw_series.get('uuid', ''))
        self.path_part = self.name.lower().replace(' ', '-')
        self.fixed_nav_entries = bool(s_config.get('fixed_nav_entries', True))
        
        # NOTE: blog path currently doesn't work for any values but None and []
        # any other path will fail
        self.blog_path = s_config.get('blog_path', [])
        if self.blog_path is False:
            self.blog_path = None
        assert self.blog_path in [[], None]

def retrieve_series(state):
    config = state.config
    
    remote = state.get_mongo()
    series_query = {
        'config.deleted': {'$ne': True}
    }
    if config.get('series'):
        series_query['name'] = {'$in': config.get('series')}
    if config['min-status'] is not None:
        series_query['config.status'] = {'$gte': config['min-status']}
    remote_series = remote.ndtest.series.find(series_query)
    remote_series = list(remote_series)
    
    return_series = [Series(raw_series, config) for raw_series in remote_series]
    
    return return_series

def retrieve_pages(state, series_list, present_series={}):
    config = state.config
    remote = state.get_mongo()
    
    return_series = series_list
    
    series_ids = [s.id for s in return_series]
    page_query = {
        'series': {'$in': series_ids}, 
    }
    if config['min-status'] is not None:
        page_query['meta.status'] = {'$gte': config['min-status']}
    
    series_uuids = {s.id: s.uuid for s in series_list}
    
    remote_uuids = remote.ndtest.pages.find(page_query, {'series': 1, 'uuid': 1, '_id': 0})
    remote_uuids = sorted(remote_uuids, key=lambda x: x.get('series') or "")
    
    uuid_hashes = {}
    for series_id, pages in groupby(remote_uuids, lambda x: x.get('series')):
        m = hashlib.sha256()
        m.update(series_uuids.get(series_id, '').encode())
        for uuid in (p.get('uuid') for p in pages):
            if not uuid:
                uuid = "8"
            m.update(uuid.encode())
        uuid_hashes[series_id] = m.hexdigest()
    
    needed_series = [s for s in return_series if s.id not in present_series or uuid_hashes[s.id] != present_series[s.id]]
    
    page_query = {
        **page_query, # include meta.status part of the query
        'series': {'$in': [s.id for s in needed_series]},
    }
    
    if not needed_series:
        remote_pages = []
    else:
        remote_pages = remote.ndtest.pages.find(page_query)
    remote_pages = list(remote_pages)

    blog_pages = [p for p in remote_pages if p['meta'].get('blog')]
    blog_pages = [p for p in blog_pages if not p['meta'].get('deleted')]

    remote_pages = [p for p in remote_pages if not p['meta'].get('deleted')]
    remote_pages = [p for p in remote_pages if not p['meta'].get('blog')]
    
    all_pages = {}

    for series in needed_series:
        hier = series.hier
        series_id = series.id
        pages = [p for p in remote_pages if p['series'] == series_id]
        series_blog_pages = [p for p in blog_pages if p['series'] == series_id]
        
        root = Page(series=series)
        all_pages[series.id] = root
        
        for page in pages:
            path = [page.get('meta', {}).get(h) for h in hier]
            path = [p for p in path if p not in [None, '', 0]]
            path = [0 if p == '_0' else p for p in path]
            path = [try_int(p, p) for p in path]
            
            path_postfix = page['meta'].get('path')
            if path_postfix:
                path.append(path_postfix)
            
            root.add_page(path, page)
        
        if series.blog_path is not None:
            for path, page in blog.process_blog_posts(series_blog_pages, series):
                if path == []:
                    for child in root:
                        child.change_root(page)
                    page.children = root.children
                    root = page
                    all_pages[series.id] = root
                else:
                    root.add_page_obj(path, page)
    
    return all_pages, return_series, uuid_hashes

def gen_fs(test_fs, all_pages, series_list, config, state, include_static=True, noisy=False):
    if not state.partial_build:
        test_fs.removetree('/')
    else:
        series_parts = [root.series.path_part for _, root in all_pages.items()]
        for d in test_fs.listdir('/'):
            if d in ['static', 'assets']:
                continue
            # don't delete files that aren't being rebuilt
            if d not in series_parts:
                continue
            if test_fs.isfile(d):
                test_fs.remove(d)
            else:
                test_fs.removetree(d)
    
    for series_id, root in all_pages.items():
        if config.series_prefix:
            test_fs.makedir(root.series.path_part)
            root.build_fs(test_fs.opendir(root.series.path_part))
        else:
            root.build_fs(test_fs)
    
    #generate an index page of series if multi series site
    if config.series_prefix:
        with test_fs.open('index.html', 'w') as f:
            f.write('<a style="color:black" href="https://nanodesutranslations.wordpress.com/"><h1>Nanodesu</h1></a>')
            for series in series_list:
                f.write('<div><a href="{}">{}</a><br></div>'.format(series.path_part, series.name))
    
    if not state.partial_build or include_static:
        with open_fs("osfs://static") as static_fs:
            fs.copy.copy_fs(static_fs, test_fs)
    try:
        image_ext = config.page_renderer.prerenderer.extensions['image']
    except (AttributeError, KeyError):
        pass
    else:
        test_fs.makedir('assets', recreate=True)
        image_ext.add_assets(test_fs.opendir('assets'))

def gen_single_page(state, page_id, *, inner_only=False,):
    single_page = page_id
    config = state.config
    
    remote = state.get_mongo()
    from bson.objectid import ObjectId
    page_id = ObjectId(single_page)
    remote_pages = remote.ndtest.pages.find({'_id': page_id})
    try:
        raw_page = next(remote_pages)
    except StopIteration:
        print("page not found")
        return {'data': 'page not found'}
    
    series_id = ObjectId(raw_page['series'])
    raw_series = remote.ndtest.series.find({'_id': series_id})
    raw_series = next(raw_series)
    series = Series(raw_series, config)
    
    root = Page(series=series)
    path = []
    root.add_page(path, raw_page)
    
    return {
        'data': root.render(inner_only=inner_only)
    }

def main():
    try:
        config_fn_i = sys.argv.index('--config')
        config_fn = sys.argv[config_fn_i + 1]
    except (ValueError, IndexError):
        config = Config()
    else:
        config = Config(config_fn)
    try:
        config_page_i = sys.argv.index('--page')
        single_page = sys.argv[config_page_i + 1]
    except (ValueError, IndexError):
        single_page = None
    try:
        config_page_out_i = sys.argv.index('-o')
        single_page_out = sys.argv[config_page_out_i + 1]
    except (ValueError, IndexError):
        single_page_out = None
    
    debug_mode = "debug" in sys.argv
    netlify_key = config.get('netlify-key')
    netlify_site_id = config.get('netlify-site-id')
    
    state = State(config)
    
    image_ext = ImageSrc(config)
    state.other['image_ext'] = image_ext
    prerenderer = PreRenderer({'image': image_ext})
    config.page_renderer = PageRenderer(config, prerenderer=prerenderer)
    
    if single_page:
        
        if single_page_out:
            res = gen_single_page(state, single_page)
            with open(single_page_out, 'w') as f:
                f.write(res['data'])
            state.close()
            import os
            # exit skipping some garbage collection
            os._exit(0)
            return
        
        test_fs = open_fs("mem://")
        with open_fs("osfs://static") as static_fs:
            fs.copy.copy_fs(static_fs, test_fs)
        
        def single_page_cb(page_id, *, inner_only=False):
            res = gen_single_page(state, page_id, inner_only=inner_only)
            return res['data']
        
        from single_page import single_page_server
        single_page_server.start_single_page_server(test_fs, single_page_cb, config['debug-server-port'], debug=debug_mode)
        
        state.close()
        return
    
    state.other['tree'] = "tree" in sys.argv
    if debug_mode:
        deploy_target = build_target.debug_target.DebugServer(state)
    elif netlify_key and netlify_site_id:
        deploy_target = build_target.netlify_target.Netlify(state)
    else:
        deploy_target = build_target.fs_target.FileSystem(state)
    
    partial_build = config['partial-builds'] and 'full' not in sys.argv
    state.partial_build = partial_build
    if partial_build:
        present_series = deploy_target.present_series()
    else:
        present_series = {}
    
    series_list = retrieve_series(state)
    all_pages, series_list, uuid_hashes = retrieve_pages(state, series_list, present_series)
    
    if uuid_hashes == present_series:
        print("NOTHING TO DO")
        state.close()
        return
    
    deploy_target.gen_fs(all_pages, series_list)
    deploy_target.post_gen(uuid_hashes)
    state.close()

if __name__ == '__main__':
    main()

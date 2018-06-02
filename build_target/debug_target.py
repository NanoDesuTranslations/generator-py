
import json

from fs import open_fs
from fs.errors import CreateFailed

import debug_server

class DebugServer:
    def __init__(self, state):
        self.state = state
        self.config = state.config
        self.series = state.series
        
        self.fs = None
        self._present_series = None
        self._regen_data = None
    
    def present_series(self):
        return {}
    
    def gen_fs(self, all_pages, series_list, *, rebuild=False):
        state = self.state
        config = self.config
        
        self._regen_data = all_pages, series_list
        
        osfs_url = "mem://{}".format(config['output-path'])
        if self.fs is None:
            self.fs = open_fs(osfs_url, create=True)
        out_fs = self.fs
        
        from build import gen_fs
        if config.url_prefix:
            out_fs.makedir(config.url_prefix, recreate=True)
            out_fs = out_fs.opendir(config.url_prefix)
        
            gen_fs(out_fs, all_pages, series_list, config, state, include_static=not rebuild)
        else:
            gen_fs(out_fs, all_pages, series_list, config, state, include_static=not rebuild)
        
        if state.other.get('tree'):
            out_fs.tree()
    
    def post_gen(self, series_uuids):
        self._present_series =series_uuids
        state = self.state
        config = self.config
        
        from build import retrieve_series, retrieve_pages
        
        def regen():
            config.load_config()
            config.page_renderer.load_templates()
            all_pages, series_list = self._regen_data
            self.gen_fs(all_pages, series_list)
        def p_reload():
            config.load_config()
            state.other['image_ext'].force_reload()
            config.page_renderer.load_templates()
            series_list = retrieve_series(state)
            all_pages, series_list, uuid_hashes = retrieve_pages(state, series_list, self._present_series)
            self._present_series = uuid_hashes
            self.gen_fs(all_pages, series_list, rebuild=True)
        def print_tree():
            self.fs.tree()
        
        special_pages = {'/regen': regen, '/reload': p_reload, '/tree': print_tree,}
        debug_server.start_debug_server(self.fs, config['debug-server-port'], special_pages)

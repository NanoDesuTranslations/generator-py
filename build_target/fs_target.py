
import json
import pickle

from fs import open_fs
from fs.errors import CreateFailed

class FileSystem:
    def __init__(self, state):
        self.state = state
        self.config = state.config
        self.series = state.series
        
        self.rebuild = False
    
    def present_series(self):
        config = self.config
        series = self.series
        cache = self.state.get_redis()
        
        lastrun = cache.get('fs_lastrun') if cache else None
        if lastrun:
            lastrun = json.loads(lastrun)
        else:
            lastrun = {}
        
        osfs_url = "osfs://{}".format(config['output-path'])
        try:
            with open_fs(osfs_url, create=False) as gen_fs:
                if not list(gen_fs.listdir('/')): # regen if output folder is empty
                    return {}
        except CreateFailed:
            return {}
        
        self.rebuild = bool(lastrun)
        return lastrun
    
    def gen_fs(self, all_pages, series_list):
        state = self.state
        config = self.config
        
        osfs_url = "osfs://{}".format(config['output-path'])
        
        from build import gen_fs
        with open_fs(osfs_url, create=True) as out_fs:
            if config.url_prefix:
                out_fs.makedir(config.url_prefix, recreate=True)
                out_fs = out_fs.opendir(config.url_prefix)
            
                gen_fs(out_fs, all_pages, series_list, config, state, include_static=not self.rebuild)
            else:
                gen_fs(out_fs, all_pages, series_list, config, state, include_static=not self.rebuild)
    
    def post_gen(self, series_uuids):
        cache = self.state.get_redis()
        config = self.config
        if cache:
            cache.set('fs_lastrun', json.dumps(series_uuids))

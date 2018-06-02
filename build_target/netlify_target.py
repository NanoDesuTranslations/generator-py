
import json

from fs import open_fs
from fs.errors import CreateFailed

class Netlify:
    def __init__(self, state):
        self.state = state
        self.config = state.config
        self.series = state.series
        
        self.lastrun = {
            'series_hashes': {},
            'netlify_hashes': {},
        }
        self.series_hashes = None
    
    def present_series(self):
        config = self.config
        series = self.series
        cache = self.state.get_redis()
        
        lastrun = cache.get('netlify_lastrun') if cache else None
        if lastrun:
            lastrun = json.loads(lastrun)
            self.lastrun = lastrun
        
        return self.lastrun['series_hashes']
    
    def _remove_old_hashes(self, series_list):
        series_path_parts = [series.path_part for series in series_list]
        # print(self.lastrun['netlify_hashes'])
        def keep_hash(h):
            parts = h.split('/')
            if not parts[0]: #remove leading /
                parts = parts[1:]
            
            # don't remove files at the root level
            if len(parts) == 1:
                return True
            spart = parts[0]
            return spart in series_path_parts or spart == 'static'
        
        self.lastrun['netlify_hashes'] = {path: h for path, h in self.lastrun['netlify_hashes'].items() if keep_hash(path)}
    
    def gen_fs(self, all_pages, series_list):
        state = self.state
        config = self.config
        
        self._remove_old_hashes(series_list)
        
        out_fs = open_fs("mem://")
        self.fs = out_fs
        
        from build import gen_fs
        if config.url_prefix:
            out_fs.makedir(config.url_prefix, recreate=True)
            out_fs = out_fs.opendir(config.url_prefix)
        
            gen_fs(out_fs, all_pages, series_list, config, state)
        else:
            gen_fs(out_fs, all_pages, series_list, config, state)
    
    def post_gen(self, series_uuids):
        config = self.config
        cache = self.state.get_redis()
        
        netlify_key = config.get('netlify-key')
        netlify_site_id = config.get('netlify-site-id')
        
        from netlify import Netlify
        netlify = Netlify(netlify_key, netlify_site_id)
        _, file_hashes = netlify.deploy_fs(self.fs, self.lastrun['netlify_hashes'])
        
        lastrun = self.lastrun
        lastrun['series_hashes'] = series_uuids
        lastrun['netlify_hashes'] = file_hashes
        if cache:
            cache.set('netlify_lastrun', json.dumps(lastrun))

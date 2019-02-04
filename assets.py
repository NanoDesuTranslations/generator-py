import os

import requests
import fs
from fs import open_fs

class ImageSrc:
    def __init__(self, config):
        self._config = config
        self.image_folder = config['image-folder']
        self.image_server = config.image_server
        
        self.used_images = set()
        
        self.images = {}
        self.remote_images = {}
        
        if self.image_folder:
            for file_name in os.listdir(config['image-folder']):
                key = file_name.rsplit('.')[0]
                path = file_name
                self.images[key] = path
        
        if self.image_server:
            headers = {
                'Cookie': 'token={}'.format(config.image_server_auth),
            }
            res = requests.get('{}/list'.format(self.image_server), headers=headers)
            
            
            img_list = res.json()
            
            for img in img_list.values():
                self.remote_images[img['file_name']] = img['url']
    
    def __call__(self, command, arg):
        try:
            url = self.remote_images[arg]
            return url
        except KeyError:
            pass
        
        try:
            path = self.images[arg]
            self.used_images.add(arg)
            return '/assets/{}'.format(path)
        except KeyError:
            return ""
    
    def force_reload(self):
        ImageSrc.__init__(self, self._config)
    
    def add_assets(self, asset_fs):
        if self.image_folder:
            with open_fs("osfs://{}".format(self.image_folder)) as static_fs:
                for key, path in self.images.items():
                    if key in self.used_images and not asset_fs.exists(path):
                        fs.copy.copy_file(static_fs, path, asset_fs, path)

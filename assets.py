import os

import fs
from fs import open_fs

class ImageSrc:
    def __init__(self, config):
        self._config = config
        self.image_folder = config['image-folder']

        self.used_images = set()

        self.images = {}
        if self.image_folder:
            for file_name in os.listdir(config['image-folder']):
                key = file_name.rsplit('.')[0]
                path = file_name
                self.images[key] = path
    
    def __call__(self, command, arg):
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
                    if key in self.used_images:
                        fs.copy.copy_file(static_fs, path, asset_fs, path)

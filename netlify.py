import hashlib

import requests

class Netlify:
    def __init__(self, key, site_id=None):
        pass
        self.host = 'api.netlify.com/api/v1'
        self.key = key
        self.site_id = site_id
        self.deploy_id = None
    
    def _make_url(self, path):
        key = self.key
        url_end = '?access_token={}'.format(key)
        url = 'https://{}/{}{}'.format(self.host, path, url_end)
        return url
    
    def _get(self, path):
        url = self._make_url(path)
        res = requests.get(url)
        return res
    
    def _post(self, path, data=None, json=None):
        url = self._make_url(path)
        res = requests.post(url, data=data, json=json)
        return res
    
    def _put_file(self, path, data=None):
        url = self._make_url(path)
        headers = {'Content-type': 'application/octet-stream'}
        res = requests.put(url, data=data, headers=headers)
        return res
    
    def sites(self):
        res = self._get('sites')
        return res.json()
    
    def create_site(self):
        res = self._post('sites')
        return res.json()
    
    def deploy(self, files):
        files = {'files': files}
        res = self._post('sites/{}/deploys'.format(site_id), json=files)
        data = res.json()
        self.deploy_id = data['id']
        return data
    
    def deploy_files(self, files):
        """Deploys files and sets deploy_id
        
            files - {path: bytes object}
        
            """
        file_digest = {
            'files': {k: hashlib.sha1(v).hexdigest() for k, v in files.items()}
        }
        res = self._post('sites/{}/deploys'.format(self.site_id), json=file_digest)
        deploy_res = res.json()
        self.deploy_id = deploy_res['id']
        required_hashes = deploy_res['required']
        by_hash = {v: k for k, v in file_digest['files'].items()}
        for file_hash in required_hashes:
            path = by_hash[file_hash]
            url = "deploys/{}/files{}".format(self.deploy_id, path)
            self._put_file(url, files[path])
        
        return deploy_res
    
    def deploy_fs(self, deploy):
        files = {
            path: deploy.getbytes(path)
            for path in deploy.walk.files()
        }
        return self.deploy_files(files)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Netlify')
    parser.add_argument('-k', '--key', required=True,
        help='netlify api key')
    parser.add_argument('command',
        choices=['create'],
        help='')
    
    args = parser.parse_args()
    if args.command == 'create':
        netlify = Netlify(args.key)
        res = netlify.create_site()
        site_id = res['site_id']
        site_name = res['name']
        print("id", site_id)
        print("name", site_name)

if __name__ == '__main__':
    main()

# Setup

* get python 3 (may require >=3.5, haven't confirmed)

* `git clone` repo
* `pip install -r requirments.txt`
* create `config/local.hjson` with `mongo-url`
* `python build.py debug tree`
* go to [http://127.0.0.1:8000](http://127.0.0.1:8000)

# Configuration

Config load path 
* `./config/default.hjson`
* `./config/local.hjson`
* file specified by `--config`

### Config values

| name             | description   |
|------------------|---------------|
| `mongo-url`      | mongo host to load data from
| `min-status`     | minimum status value for pages to include
| `output-path`    | path to output generated files to
| `series`         | optional array of series to include (by name)
| `url-prefix`     | prefix for paths
| `series_prefix`  | can be set to false to place the series at the root of the filesystem instead of creating a top level index page. should be used with a single item in `series`
| `include-raw`    | can be set to false to disabled generation of pages containing the unprocessed content of pages
| `enabled.disqus` | enables disqus embed
| `enabled.google-analytics` | enables google analytics tracking of page views
| `enabled.social-media` | enables facebook and twitter embeds
| `ftp-info`       | can be null or contain info for an ftp server to upload to
| `ftp-info.host`  | hostname of ftp server
| `ftp-info.user`  | ftp user
| `ftp-info.pass`  | ftp password
| `debug-server-port` | port to run debug server on

# Args

#### `--config <file>`

Loads the config file at `./config/<file>.hjson` in addition to the normal config files.

#### `debug`

Starts a debug server instead of writing to the file system.

#### `tree`

Only supported with debug. Prints the generated file tree to the console.

#### `static`

Only supported when uploading to ftp. Uploads static files. Normally static files are not deleted or uploaded with the assumption they have not changed.

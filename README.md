Cporter
======

Cporter, sync files between Cloud Storage [Dropbox, UpYun, Qiniu, ...]

### INSTALL

	# pip install cporter

### USAGE
	
	# cporter --help
	
	Usage: cporter.py [OPTIONS] COMMAND [ARGS]...

	  Cporter, sync files between Cloud Storage [Dropbox, UpYun, Qiniu]

	Commands:
	  clean   delete config file.
	  config  config <storage> to sync.
	  sync    sync files between <source> and <dest>.

	Options:
	  --version  Show the version and exit.
	  --help     Show this message and exit.


### TODO
- ~~Package~~
- ~~sync upyun to qiniu~~
- ~~sync dropbox to qiniu~~
- sync qiniu to upyun/dropbox
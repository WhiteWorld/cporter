# -*- coding: utf8 -*-
import upyun
import dropbox
import click
import ConfigParser

config = ConfigParser.RawConfigParser()
config.read(".porter")

def init_upyun():
	BUCKETNAME = config.get('UpYun',"BUCKETNAME")
	USERNAME = config.get('UpYun', "USERNAME")
	PASSWORD = config.get('UpYun', "PASSWORD")
	return upyun.UpYun(BUCKETNAME, USERNAME, PASSWORD)

def init_dropbox():
	APP_KEY = config.get("Dropbox","APP_KEY")
	APP_SECRET = config.get("Dropbox", "APP_SECRET")
	try:
		ACCESS_TOKEN = config.get("Dropbox", "ACCESS_TOKEN")
	except ConfigParser.NoOptionError:
		flow = dropbox.client.DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)
		# Have the user sign in and authorize this token
		authorize_url = flow.start()
		print '1. Go to: ' + authorize_url
		print '2. Click "Allow" (you might have to log in first)'
		print '3. Copy the authorization code.'
		code = raw_input("Enter the authorization code here: ").strip()
		# This will fail if the user enters an invalid authorization code
		access_token, user_id = flow.finish(code)
		config.set("Dropbox", "ACCESS_TOKEN", access_token)
		with open('.porter', 'w') as f:
			config.write(f)
		print access_token,user_id
        #config = read(".porter")
        ACCESS_TOKEN = config.get("Dropbox", "ACCESS_TOKEN")
	return dropbox.client.DropboxClient(ACCESS_TOKEN)
	
def Upyun2DropboxFile(filepath, up_client, dropbox_client):
    f = up_client.get(filepath)
    dropbox_client.put_file(filepath, f, True, True);


def Upyun2DropboxDir(dir, up_client, dropbox_client):
    res = up_client.getlist(dir)
    for item in res:
        path = dir + item['name']
        print path
        if item['type'] == 'F':
            Upyun2DropboxDir(path+'/', up_client, dropbox_client)
        else:
            Upyun2DropboxFile(path, up_client, dropbox_client)


def Dropbox2UpyunFile(filepath, up_client, dropbox_client):
    print filepath
    with dropbox_client.get_file(filepath) as f:
        up_client.put(filepath, f.read())


def Dropbox2UpyunDir(dir, up_client, dropbox_client):
    res = dropbox_client.metadata(dir)
    if res['is_dir'] == False:
        Dropbox2UpyunFile(res['path'], up_client, dropbox_client)
    else:
        for item in res.get('contents', []):
            if item['is_dir'] == False:
                Dropbox2UpyunFile(item['path'], up_client, dropbox_client)
            else:
                Dropbox2UpyunDir(item['path'], up_client, dropbox_client)

@click.command()
@click.argument('source', metavar='<source>', required=True)
@click.argument('dest', metavar='<dest>', required=True)
def main(source, dest):
    """source/dest: now support "upyun" "dropbox"   """
    if source == 'upyun' and dest=='dropbox':
    	dropbox_client = init_dropbox()
    	up_client = init_upyun()
        Upyun2DropboxDir('/', up_client, dropbox_client)
    elif source == 'dropbox' and dest == 'upyun':
    	up_client = init_upyun()
    	dropbox_client = init_dropbox()
        Dropbox2UpyunDir('/', up_client, dropbox_client)
    else:
        print "please input right source and dest"

if __name__ == '__main__':
    main()
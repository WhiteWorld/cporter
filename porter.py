# -*- coding: utf8 -*-
import upyun
import dropbox
import click
import ConfigParser
import os
import sys

APP_CREATE_URL="https://www2.dropbox.com/developers/apps"

config = ConfigParser.RawConfigParser()

home = os.path.expanduser("~")

config_file_path=home+'/.porter'

#config.read(config_file_path)

def set_config_file(filepath):
    if not os.path.isfile(filepath):
        with open(filepath, 'w+') as f:
            print "This is the first time you run this."
            print "*********************Config Upyun****************************************"
            while True:
                bucketname = raw_input('Enter bucketname: ')
                username = raw_input('Enter username: ')
                password = raw_input('Enter password: ')
                ok = raw_input('The bucketname is '+bucketname+', username is '+username+', password is '+password+'. Looks ok? [y/n]')
                if ok == 'y' or ok == 'Y':
                    break
            f.write("[UpYun]\n")
            f.write('bucketname='+bucketname+'\n')
            f.write('username='+username+'\n')
            f.write('password='+password+'\n')


            print "*********************Config Dropbox****************************************"
            print " 1) Open the following URL in your Browser, and log in using your account: " + APP_CREATE_URL
            print " 2) Click on 'Create App', then select 'Dropbox API app'"
            print " 3) Select 'Files and datastores'"
            print " 4) Now go on with the configuration, choosing the app permissions and access restrictions to your DropBox folder"
            print " 5) Enter the 'App Name' that you prefer (e.g. UpYun)"

            print " Now, click on the 'Create App' button."

            print " When your new App is successfully created, please type the App Key, App Secret and the Permission type shown in the confirmation page:"
            while True:
                app_key = raw_input('Enter App key: ')
                app_secret = raw_input('Enter App secret: ')
                ok = raw_input("The App key is "+app_key+" , App secret is "+app_secret+". Looks OK? [y/n]")
                if ok == 'y' or ok == 'Y':
                    break
            f.write('[Dropbox]\n')
            f.write('app_key='+app_key+'\n')
            f.write('app_secret='+app_secret+'\n')

    config.read(config_file_path)

def init_upyun():
    try:
        BUCKETNAME = config.get("UpYun","bucketname")
        USERNAME = config.get('UpYun', "username")
        PASSWORD = config.get('UpYun', "password")
    except ConfigParser.NoOptionError:
        print "Please set bucketname username password in "+ config_file_path +" (in section [UpYun])."
        sys.exit()
    return upyun.UpYun(BUCKETNAME, USERNAME, PASSWORD)

def init_dropbox():
    try:
        APP_KEY = config.get("Dropbox","app_key")
        APP_SECRET = config.get("Dropbox", "app_secret")
    except ConfigParser.NoOptionError:
        print "Please set app_key app_secret in "+ config_file_path +" (in section [Dropbox])."
        sys.exit()
    try:
        ACCESS_TOKEN = config.get("Dropbox", "access_token")
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
        config.set("Dropbox", "access_token", access_token)
        with open(config_file_path, 'w') as f:
            config.write(f)
        print access_token,user_id
        #config = read(".porter")
        ACCESS_TOKEN = config.get("Dropbox", "access_token")
    return dropbox.client.DropboxClient(ACCESS_TOKEN)
    
def Upyun2DropboxFile(filepath, up_client, dropbox_client):
    print "Sync..."+filepath
    f = up_client.get(filepath)
    dropbox_client.put_file(filepath, f, overwrite=True);


def Upyun2DropboxDir(dir, up_client, dropbox_client):
    res = up_client.getlist(dir)
    for item in res:
        path = dir + item['name']
        #print path
        if item['type'] == 'F':
            Upyun2DropboxDir(path+'/', up_client, dropbox_client)
        else:
            Upyun2DropboxFile(path, up_client, dropbox_client)


def Dropbox2UpyunFile(filepath, up_client, dropbox_client):
    print "Sync..."+filepath
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

@click.group()
@click.version_option("v0.1", prog_name="porter")
def cli():
    """Porter, sync files between UpYun,Dropbox and so on."""
    pass


@click.command()
@click.argument('source', metavar='<source>', required=True)
@click.argument('dest', metavar='<dest>', required=True)
def sync(source, dest):
    """sync files between <source> and <dest>"""#, now support [upyun, dropbox]"""
    set_config_file(config_file_path)
    if source == 'upyun' and dest=='dropbox':
        dropbox_client = init_dropbox()
        up_client = init_upyun()
        Upyun2DropboxDir('/', up_client, dropbox_client)
    elif source == 'dropbox' and dest == 'upyun':
        up_client = init_upyun()
        dropbox_client = init_dropbox()
        Dropbox2UpyunDir('/', up_client, dropbox_client)
    else:
        print "Please input right source and dest."



@click.command()
def clean():
    """ delete config file """
    ## if file exists, delete it ##
    if os.path.isfile(config_file_path):
        os.remove(config_file_path)
    else:    ## Show an error ##
        print("Error: %s file not found" % config_file_path)

cli.add_command(sync)
cli.add_command(clean)

if __name__ == '__main__':
    cli()
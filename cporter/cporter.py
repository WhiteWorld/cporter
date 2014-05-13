# -*- coding: utf8 -*-
import upyun
import dropbox

import click
import ConfigParser
import os
import sys

import qiniu.conf
import qiniu.rs
import qiniu.io

APP_CREATE_URL="https://www2.dropbox.com/developers/apps"

config = ConfigParser.RawConfigParser()

home = os.path.expanduser("~")

config_file_path=home + '.cporter'

VERSION = '0.2.0'

SUPPORT = "[UpYun, Dropbox, Qiniu]"

def create_config_file():
    if not os.path.isfile(config_file_path):
        config = ConfigParser.RawConfigParser(allow_no_value=True)

        config.add_section('UpYun')
        config.add_section('Dropbox')
        config.add_section('Qiniu')

        with open(config_file_path, 'wb') as f:
            print "create the config file:"+config_file_path
            config.write(f)

def init_upyun(config):
    try:
        BUCKETNAME = config.get("UpYun","bucketname")
        USERNAME = config.get('UpYun', "username")
        PASSWORD = config.get('UpYun', "password")
    except ConfigParser.NoOptionError:
        print "Run 'cporter config upyun' command first."
        sys.exit()
    return upyun.UpYun(BUCKETNAME, USERNAME, PASSWORD)

def init_qiniu(config):
    try:
        BUCKETNAME = config.get("Qiniu","bucketname")
        ACCESS_KEY = config.get('Qiniu', "access_key")
        SECRET_KEY = config.get('Qiniu', "secret_key")
    except ConfigParser.NoOptionError:
        print "Run 'cporter config qiniu' command first."
        sys.exit()
    qiniu.conf.ACCESS_KEY = ACCESS_KEY
    qiniu.conf.SECRET_KEY = SECRET_KEY
    policy = qiniu.rs.PutPolicy(BUCKETNAME)
    uptoken = policy.token()
    return qiniu, uptoken

def init_dropbox(config):
    try:
        APP_KEY = config.get("Dropbox","app_key")
        APP_SECRET = config.get("Dropbox", "app_secret")
    except ConfigParser.NoOptionError:
        print "Run 'cporter config dropbox' command first."
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
        with open(config_file_path, 'wb') as f:
            config.write(f)
        print access_token,user_id
        #config = read(".porter")
        ACCESS_TOKEN = config.get("Dropbox", "access_token")
    return dropbox.client.DropboxClient(ACCESS_TOKEN)
    
def Upyun2DropboxFile(filepath, up_client, dropbox_client):
    print "Sync..."+filepath
    f = up_client.get(filepath)
    dropbox_client.put_file(filepath, f, overwrite=True)

def Upyun2DropboxDir(dir, up_client, dropbox_client):
    res = up_client.getlist(dir)
    for item in res:
        path = dir + item['name']
        #print path
        if item['type'] == 'F':
            Upyun2DropboxDir(path+'/', up_client, dropbox_client)
        else:
            Upyun2DropboxFile(path, up_client, dropbox_client)

def Upyun2QiniuFile(filepath, up_client, qiniu_client, uptoken):
    print "Sync..."+filepath
    f = up_client.get(filepath)
    ret, err = qiniu_client.io.put(uptoken,filepath,f)
    if err is not None:
        sys.stderr.write('error: %s ' % err)

def Upyun2QiniuDir(dir, up_client, qiniu_client, uptoken):
    res = up_client.getlist(dir)
    for item in res:
        path = dir + item['name']
        if item['type'] == 'F':
            Upyun2QiniuDir(path+'/', up_client, qiniu_client, uptoken)
        else:
            Upyun2QiniuFile(path, up_client, qiniu_client, uptoken)

def Dropbox2UpyunFile(filepath, dropbox_client, up_client):
    print "Sync..."+filepath
    with dropbox_client.get_file(filepath) as f:
        up_client.put(filepath, f.read())

def Dropbox2UpyunDir(dir, dropbox_client, up_client):
    res = dropbox_client.metadata(dir)
    if res['is_dir'] == False:
        Dropbox2UpyunFile(res['path'], dropbox_client, up_client)
    else:
        for item in res.get('contents', []):
            if item['is_dir'] == False:
                Dropbox2UpyunFile(item['path'], dropbox_client, up_client)
            else:
                Dropbox2UpyunDir(item['path'], dropbox_client, up_client)

def Dropbox2QiniuFile(filepath, dropbox_client, qiniu_client, uptoken):
    print "Sync..."+filepath
    with dropbox_client.get_file(filepath) as f:
        ret, err = qiniu_client.io.put(uptoken,filepath,f)
        if err is not None:
            sys.stderr.write('error: %s ' % err)

def Dropbox2QiniuDir(dir, dropbox_client, qiniu_client, uptoken):
    res = dropbox_client.metadata(dir)
    if res['is_dir'] == False:
        Dropbox2QiniuFile(res['path'], dropbox_client, qiniu_client, uptoken)
    else:
        for item in res.get('contents', []):
            if item['is_dir'] == False:
                Dropbox2QiniuFile(item['path'], dropbox_client, qiniu_client, uptoken)
            else:
                Dropbox2QiniuDir(item['path'], dropbox_client, qiniu_client, uptoken)

# not used
def list_all(bucket, rs=None, prefix=None, limit=None):
    if rs is None:
        rs = qiniu.rsf.Client()
    marker = None
    err = None
    while err is None:
        ret, err = rs.list_prefix(bucket_name, prefix=prefix, limit=limit, marker=marker)
        marker = ret.get('marker', None)
        for item in ret['items']:
            #do something
            pass
    if err is not qiniu.rsf.EOF:
        # 错误处理
        pass




@click.command()
@click.argument('source', metavar='<source>', required=True)
@click.argument('dest', metavar='<dest>', required=True)
def sync(source, dest):
    """sync files between <source> and <dest>"""#, now support [upyun, dropbox]"""
    if not os.path.isfile(config_file_path):
        print "Please config first"
        return
    config = ConfigParser.RawConfigParser()
    config.read(config_file_path)
    if source == 'upyun' and dest=='dropbox':
        dropbox_client = init_dropbox(config)
        up_client = init_upyun(config)
        Upyun2DropboxDir('/', up_client, dropbox_client)
    elif source == 'dropbox' and dest == 'upyun':
        up_client = init_upyun(config)
        dropbox_client = init_dropbox(config)
        Dropbox2UpyunDir('/', dropbox_client, up_client)
    elif source == 'upyun' and dest == 'qiniu':
        qiniu_client,uptoken = init_qiniu(config)
        up_client = init_upyun(config)
        Upyun2QiniuDir('/', up_client, qiniu_client, uptoken)
    elif source == 'dropbox' and dest == 'qiniu':
        dropbox_client = init_dropbox(config)
        qiniu_client = init_qiniu(config)
        Dropbox2QiniuDir('/', dropbox_client, qiniu_client, uptoken)
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


def print_hint(str):
    first = '*'*((80-len(str))/2)
    print first+str+first


def config_upyun():
    """ config upyun """
    print_hint("Config UpYun")
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(config_file_path)
    while True:
        bucketname = raw_input('Enter bucketname: ')
        username = raw_input('Enter username: ')
        password = raw_input('Enter password: ')
        ok = raw_input('The bucketname is '+bucketname+', username is '+username+', password is '+password+'. Looks ok? [y/n]')
        if ok == 'y' or ok == 'Y':
            break
    config.set('UpYun', 'bucketname', bucketname)
    config.set('UpYun', 'username', username)
    config.set('UpYun', 'password', password)
    with open(config_file_path, 'wb') as f:
        config.write(f)

def config_qiniu():
    """ config qiniu """
    print_hint("Config Qiniu")
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(config_file_path)
    while True:
        bucketname = raw_input('Enter bucketname: ')
        access_key = raw_input('Enter access_key: ')
        secret_key = raw_input('Enter secret_key: ')
        ok = raw_input('The bucketname is '+bucketname+', access_key is '+access_key+', secret_key is '+secret_key+'. Looks ok? [y/n]')
        if ok == 'y' or ok == 'Y':
            break
    config.set('Qiniu', 'bucketname', bucketname)
    config.set('Qiniu', 'access_key', access_key)
    config.set('Qiniu', 'secret_key', secret_key)
    with open(config_file_path, 'wb') as f:
        config.write(f)


def config_dropbox():
    """ config Dropbox """
    print_hint("Config Dropbox")
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(config_file_path)
    while True:
        app_key = raw_input('Enter app_key: ')
        app_secret = raw_input('Enter app_secret: ')
        ok = raw_input('The app_key is '+app_key+', app_secret is '+app_secret+'. Looks ok? [y/n]')
        if ok == 'y' or ok == 'Y':
            break
    config.set('Dropbox', 'app_key', app_key)
    config.set('Dropbox', 'app_secret', app_secret)
    with open(config_file_path, 'wb') as f:
        config.write(f)





@click.command()
@click.argument('storage', metavar='<Cloud Storage>', required=True)
def config(storage):
    """ config <storage> to sync"""
    create_config_file()
    if storage == 'upyun':
        config_upyun()
    elif storage == 'dropbox':
        config_dropbox()
    elif storage == 'qiniu':
        config_qiniu()
    else:
        print "Only support:"+SUPPORT

@click.group()
@click.version_option(VERSION, prog_name="cporter")
def main():
    """Cporter, sync files between Cloud Storage [Dropbox, UpYun, Qiniu]"""
    pass


main.add_command(sync)
main.add_command(clean)
main.add_command(config)

if __name__ == '__main__':
    main()
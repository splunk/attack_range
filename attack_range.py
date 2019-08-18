import os
import argparse
import wget
import requests
import urllib.parse
import re
import vagrant
import shutil


VERSION = 1

def grab_splunk(bin_dir):
    print("\ngrabbing splunk enterprise server for linux\n")
    url = 'https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=linux&version=7.3.1&product=splunk&filename=splunk-7.3.1-bd63e13aa157-Linux-x86_64.tgz&wget=true'
    output = bin_dir + '/splunk-7.3.1-bd63e13aa157-Linux-x86_64.tgz'
    wget.download(url,output)
    ansible_role_path_dst = 'ansible/roles/search_head/files/' + 'splunk-7.3.1-bd63e13aa157-Linux-x86_64.tgz'
    shutil.copy2(output, ansible_role_path_dst)
#    os.symlink(output, splunk)

def grab_splunk_ta(bin_dir):
    print("\ngrabbing splunk forwarder for windows\n")
    url = 'https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=windows&version=7.3.0&product=universalforwarder&filename=splunkforwarder-7.3.0-657388c7a488-x64-release.msi&wget=true'
    output = bin_dir + '/splunkforwarder-7.3.0-657388c7a488-x64-release.msi'
    wget.download(url,output)
    ansible_role_path_dst = 'ansible/roles/universal_forwarder/files' + '/splunkforwarder-7.3.0-657388c7a488-x64-release.msi'
    shutil.copy2(output, ansible_role_path_dst)
#    os.symlink(output, splunk)

def grab_splunkbase_token(splunkbase_username, splunkbase_password):
    api_url = 'https://splunkbase.splunk.com/api/account:login/'
    payload = 'username={0}&password={1}'.format(splunkbase_username, splunkbase_password)
    headers = {"Content-Type":"application/x-www-form-urlencoded", "Accept":"*/*"}
    response = requests.post(api_url, headers=headers, data=payload)
    if response.status_code != 200:
        raise Exception("Invalid Splunkbase credentials - will not download apps from Splunkbase")
    output = response.text
    splunkbase_token = re.search("<id>(.*)</id>", output, re.IGNORECASE)
    sb_token = splunkbase_token.group(1) if splunkbase_token else None
    return sb_token


if __name__ == "__main__":
    # grab arguments
    parser = argparse.ArgumentParser(description="starts a attack range ready to collect attack data into splunk") 
    parser.add_argument("-b", "--appbin", required=False, default="appbinaries", help="directory to store binaries in")
    parser.add_argument("-m", "--mode", required=False, default="terraform", help="mode of operation, terraform/vagrant, please see configuration for each at: https://github.com/splunk/attack_range")
    parser.add_argument("-s", "--state", required=False, default="up", help="state of the range, defaults to \"up\", up/down allowed")
    parser.add_argument("-sbu", "--splunkbase_username", required=True, default="", help="splunkbase username, used to download apps")
    parser.add_argument("-sbp", "--splunkbase_password", required=True, default="", help="splunkbase password, used to download apps")
    parser.add_argument("-v", "--version", required=False, help="shows current attack_range version")

    # parse them
    args = parser.parse_args()
    ARG_VERSION = args.version
    bin_dir = args.appbin
    splunkbase_username = args.splunkbase_username
    splunkbase_password = args.splunkbase_password
    mode = args.mode
    state = args.state

    print("INIT - Attack Range v" + str(VERSION))
    print("""
starting program loaded for mode - B1 battle droid

  ||/__'`.
  |//()'-.:
  |-.||
  |o(o)
  |||\\\  .==._
  |||(o)==::'
   `|T  ""
    ()
    |\\
    ||\\
    ()()
    ||//
    |//
   .'=`=.
    """)

    if ARG_VERSION:
        print ("version: {0}".format(VERSION))
        sys.exit()

    if os.path.exists(bin_dir):
        print ("this is not our first run binary directory exists, skipping setup")
    else:
        print ("seems this is our first run, creating a directory for binaries at {0}".format(bin_dir))
        os.makedirs(bin_dir)
        grab_splunk(bin_dir)
        grab_splunk_ta(bin_dir)

    sb_token = grab_splunkbase_token(splunkbase_username, splunkbase_password)
    if mode == "vagrant":
        print ("[mode] > vagrant")
        if state == "up":
            print ("[state] > up")
            vagrantfile = 'vagrant/splunk_server/'
            v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
            #v1.destroy()
            v1.up()
        elif state == "down":
            print ("[state] > down")
            vagrantfile = 'vagrant/splunk_server/'
            v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
            v1.destroy()
        else:
            print("incorrect state, please set flag --state to \"up\" or \"download\"")

    # lets process modes
    elif mode == "terraform":
        print("[mode] > terraform ")
        print("not yet implemented")
    else:
        print("incorrect mode, please set flag --mode to \"terraform\" or \"vagrant\"")





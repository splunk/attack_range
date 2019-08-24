import os
import sys
import argparse
import wget
import requests
import urllib.parse
import re
import vagrant
import shutil
from python_terraform import *

# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

VERSION = 1

def grab_splunk(bin_dir):
    print("\ngrabbing splunk enterprise server for linux\n")
    url = 'https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=linux&version=7.3.1&product=splunk&filename=splunk-7.3.1-bd63e13aa157-Linux-x86_64.tgz&wget=true'
    output = bin_dir + '/splunk-7.3.1-bd63e13aa157-Linux-x86_64.tgz'
    wget.download(url,output)

def grab_splunk_uf_win(bin_dir):
    print("\ngrabbing splunk forwarder for windows\n")
    url = 'https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=windows&version=7.3.0&product=universalforwarder&filename=splunkforwarder-7.3.0-657388c7a488-x64-release.msi&wget=true'
    output = bin_dir + '/splunkforwarder-7.3.0-657388c7a488-x64-release.msi'
    wget.download(url,output)

def grab_splunk_ta_win(bin_dir):
    print("\ngrabbing splunk add-on for windows\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/splunk-add-on-for-microsoft-windows_600.tgz'
    output = bin_dir + '/splunk-add-on-for-microsoft-windows_600.tgz'
    wget.download(url,output)

def grab_splunk_ta_sysmon(bin_dir):
    print("\ngrabbing splunk add-on for sysmon\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/add-on-for-microsoft-sysmon_800.tgz'
    output = bin_dir + '/add-on-for-microsoft-sysmon_800.tgz'
    wget.download(url,output)

def grab_splunk_cim_app(bin_dir):
    print("\ngrabbing splunk (CIM) common information model app\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/splunk-common-information-model-cim_4130.tgz'
    output = bin_dir + '/splunk-common-information-model-cim_4130.tgz'
    wget.download(url,output)

def grab_streams(bin_dir):
    print("\ngrabbing splunk stream app\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/splunk-stream_713.tgz'
    output = bin_dir + '/splunk-stream_713.tgz'
    wget.download(url,output)
    print("\ngrabbing splunk stream TA\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/Splunk_TA_stream.zip'
    output = bin_dir + '/Splunk_TA_stream.zip'
    wget.download(url,output)

def grab_firedrill(bin_dir):
    print("\ngrabbing firedrill agent\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/FiredrillAgent-installer-2.2.389.exe'
    output = bin_dir + '/FiredrillAgent-installer-2.2.389.exe'
    wget.download(url,output)

def grab_escu_latest(bin_dir):
    print("\ngrabbing splunk ESCU app\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/DA-ESS-ContentUpdate-v1.0.41.tar.gz'
    output = bin_dir + '/DA-ESS-ContentUpdate-v1.0.41.tar.gz'
    wget.download(url,output)


if __name__ == "__main__":
    # grab arguments
    parser = argparse.ArgumentParser(description="starts a attack range ready to collect attack data into splunk") 
    parser.add_argument("-b", "--appbin", required=False, default="appbinaries", help="directory to store binaries in")
    parser.add_argument("-m", "--mode", required=True, default="terraform", help="mode of operation, terraform/vagrant, please see configuration for each at: https://github.com/splunk/attack_range")
    parser.add_argument("-s", "--state", required=True, default="up", help="state of the range, defaults to \"up\", up/down allowed")
    parser.add_argument("-v", "--version", required=False, help="shows current attack_range version")
    parser.add_argument("-vbox", "--vagrant_box", required=False, default="", help="select which vagrant box to stand up or destroy individually")
    parser.add_argument("-vls", "--vagrant_list", required=False, default=False, action="store_true", help="prints out all avaiable vagrant boxes")

    # parse them
    args = parser.parse_args()
    ARG_VERSION = args.version
    bin_dir = args.appbin
    mode = args.mode
    state = args.state
    vagrant_box = args.vagrant_box
    vagrant_list = args.vagrant_list

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
        sys.exit(1)

    if os.path.exists(bin_dir):
        print ("this is not our first run binary directory exists, skipping setup")
    else:
        print ("seems this is our first run, creating a directory for binaries at {0}".format(bin_dir))
        os.makedirs(bin_dir)
        grab_splunk(bin_dir)
        grab_splunk_uf_win(bin_dir)
        grab_splunk_ta_win(bin_dir)
        grab_splunk_ta_sysmon(bin_dir)
        grab_splunk_cim_app(bin_dir)
        grab_streams(bin_dir)
        grab_firedrill(bin_dir)
        grab_escu_latest(bin_dir)

    if vagrant_list:
        print("available VAGRANT BOX:\n")
        d = 'vagrant'
        subdirs = os.listdir(d)
        for f in subdirs:
            if f == ".vagrant" or f == "Vagrantfile":
                continue
            print("* " + f)
        sys.exit(1)

    if mode == "vagrant":
        print ("[mode] > vagrant")
        if vagrant_box:
            vagrantfile = 'vagrant/' + vagrant_box
            print("operating on vagrant box: " + vagrantfile)
        else:
            vagrantfile = 'vagrant/' 
            print("operating on all range boxes WARNING MAKE SURE YOU HAVE 16GB OF RAM otherwise you will have a bad time")
        if state == "up":
            print ("[state] > up")
            v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
            #v1.destroy()
            v1.up(provision=True)
        elif state == "down":
            print ("[state] > down")
            v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
            v1.destroy()
        else:
            print("incorrect state, please set flag --state to \"up\" or \"download\"")

    # lets process modes
    elif mode == "terraform":
        print("[mode] > terraform ")
        if state == "up":
            print ("[state] > up")
            t = Terraform(working_dir='terraform')
            return_code, stdout, stderr = t.apply(capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
            print("TERRAFORM COMPLETED WITH RETURN CODE {0}".format(return_code))
        elif state == "down":
            print ("[state] > down")
            t = Terraform(working_dir='terraform')
            return_code, stdout, stderr = t.destroy(capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
            print("TERRAFORM COMPLETED WITH RETURN CODE {0}".format(return_code))
        else:
            print("incorrect state, please set flag --state to \"up\" or \"download\"")
    else:
        print("incorrect mode, please set flag --mode to \"terraform\" or \"vagrant\"")





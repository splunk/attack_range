#!/usr/bin/python

'''
Helps configure your attack_range before using.
'''

import sys
from pathlib import Path
import argparse
import urllib.request
from PyInquirer import prompt, Separator
import configparser
import random
import string
import boto3
from botocore.config import Config
import getpass
import time
import os



CONFIG_TEMPLATE = 'attack_range.conf.template'

def load_config_template(CONFIG_TEMPLATE):
    settings = {}
    config = configparser.RawConfigParser()
    config.read(CONFIG_TEMPLATE)
    return config

def get_random_password():
    random_source = string.ascii_letters + string.digits
    password = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)

    for i in range(16):
        password += random.choice(random_source)

    password_list = list(password)
    random.SystemRandom().shuffle(password_list)
    password = ''.join(password_list)
    return password

def create_key_pair(client):
    # create new ssh key new_key_pair
    epoch_time = str(int(time.time()))
    ssh_key_name = getpass.getuser() + "-" + epoch_time[-5:] + ".key"
    # create ssh keys
    response = client.create_key_pair(KeyName=ssh_key_name)
    with open(ssh_key_name, "w") as ssh_key:
        ssh_key.write(response['KeyMaterial'])
    os.chmod(ssh_key_name, 0o600)

    return ssh_key_name


def main(args):
    # grab args
    parser = argparse.ArgumentParser(
        description="Use `setup.py` is a tool used to install and configure attack_range")
    parser.add_argument("-c", "--config", required=False, default="attack_range.conf",
                        help="path to where you want to store the configuration file of attack_range")
    args = parser.parse_args()
    config = args.config

    # parse config
    attack_range_config = Path(config)
    if attack_range_config.is_file():
        questions = [
        {
            'type': 'confirm',
            'message': 'File {0} already exist, are you sure you want to continue?\nTHIS WILL OVERWRITE YOUR CURRENT CONFIG!'.format(attack_range_config),
            'name': 'continue',
            'default': True,
        },
        ]

        answers = prompt(questions)
        if answers['continue']:
            print("> continuing with attack_range configuration...")
        else:
            print("> exiting, to create a unique configuration file in another location use the --config flag")
            parser.print_help()
            sys.exit(0)

        configpath = str(attack_range_config)

    print("""
           ________________
         |'-.--._ _________:
         |  /    |  __    __\\\\
         | |  _  | [\\_\\= [\\_\\
         | |.' '. \\.........|
         | ( <)  ||:       :|_
          \\ '._.' | :.....: |_(o
           '-\\_   \\ .------./
           _   \\   ||.---.||  _
          / \\  '-._|/\\n~~\\n' | \\\\
         (| []=.--[===[()]===[) |
         <\\_/  \\_______/ _.' /_/
         ///            (_/_/
         |\\\\            [\\\\
         ||:|           | I|
         |::|           | I|
         ||:|           | I|
         ||:|           : \\:
         |\\:|            \\I|
         :/\\:            ([])
         ([])             [|
          ||              |\\_
         _/_\\_            [ -'-.__
    snd <]   \\>            \\_____.>
          \\__/

starting configuration for AT-ST mech walker
    """)

    configuration = load_config_template(CONFIG_TEMPLATE)
    questions = [
        {
            # get provider
            'type': 'list',
            'message': 'select cloud provider',
            'name': 'cloud_provider',
            'choices': [
                {
                    'name': 'aws'
                },
                {
                    'name': 'azure'
                },
            ],
        },
        {
            # get api_key
            'type': 'input',
            'message': 'enter azure subscription id',
            'name': 'azure_subscription_id',
            'when': lambda answers: answers['cloud_provider'] == 'azure',
        },
        {
            # get range password
            'type': 'input',
            'message': 'enter a master password for your attack_range',
            'name': 'attack_range_password',
            'default': get_random_password(),
        },
    ]
    answers = prompt(questions)
    if answers['cloud_provider'] == 'aws':
        aws_session = boto3.Session()
        if aws_session.region_name:
            aws_configured_region = aws_session.region_name
        else:
            print("ERROR aws region not configured, please run `aws configure` to setup awscli")
            sys.exit(1)
    configuration._sections['global']['cloud_provider'] = answers['cloud_provider']
    configuration._sections['global']['attack_range_password'] = answers['attack_range_password']
    if 'azure_subscription_id' in answers:
        configuration._sections['azure']['azure_subscription_id'] = answers['azure_subscription_id']
    else:
        configuration._sections['azure']['azure_subscription_id'] = 'xxxXXX'

    print("> configuring attack_range settings")
    # get external IP for default suggestion on whitelist question
    external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
    questions = [
        {   # new key pair?
            'type': 'confirm',
            'message': 'generate a new ssh key pair for this range',
            'name': 'new_key_pair',
            'default': True,
        },
        {
            # get api_key
            'type': 'input',
            'message': 'enter ssh key name',
            'name': 'key_name',
            'when': lambda answers: answers['new_key_pair'] == False,
        },
        {
            # get private_key_path
            'type': 'input',
            'message': 'enter private key path for machine access',
            'name': 'private_key_path',
            'default': "~/.ssh/id_rsa",
            'when': lambda answers: answers['new_key_pair'] == False,
        },
        {
            # get public_key_path
            'type': 'input',
            'message': 'enter public key path for machine access',
            'name': 'public_key_path',
            'default': "~/.ssh/id_rsa.pub",
            'when': lambda answers: answers['new_key_pair'] == False,
        },
        {
            # get region
            'type': 'input',
            'message': 'enter aws region to build in.',
            'name': 'region',
            'default': aws_configured_region,
            'when': lambda  answers: configuration._sections['global']['cloud_provider'] == 'aws',
        },
        {
            # get whitelist
            'type': 'input',
            'message': 'enter public ips that are allowed to reach the attack_range.\nExample: {0}/32,0.0.0.0/0'.format(external_ip),
            'name': 'ip_whitelist',
            'default': external_ip + "/32"
        },
        {
            # get range name
            'type': 'input',
            'message': 'enter attack_range name, multiple can be build under different names in the same region',
            'name': 'range_name',
            'default': "default",
        },

    ]
    answers = prompt(questions)
    if answers['new_key_pair']:
        # create new ssh key new_key_pair
        new_key_name = create_key_pair(aws_session.client('ec2', region_name=answers['region']))
        new_key_path = Path(new_key_name).resolve()
        configuration._sections['range_settings']['key_name'] = new_key_name
        configuration._sections['range_settings']['private_key_path'] = str(new_key_path)
        print("> new aws ssh created: {}".format(new_key_path))
    else:
        configuration._sections['range_settings']['key_name'] = answers['key_name']
        configuration._sections['range_settings']['private_key_path'] = answers['private_key_path']

    if 'public_key_path' in answers:
        configuration._sections['range_settings']['public_key_path'] = answers['public_key_path']
    else:
        configuration._sections['range_settings']['public_key_path'] = '~/.ssh/id_rsa.pub'
    if 'region' in answers:
        configuration._sections['range_settings']['region'] = answers['region']
    else:
        configuration._sections['range_settings']['region'] = 'us-west-2'
    configuration._sections['range_settings']['ip_whitelist'] = answers['ip_whitelist']
    configuration._sections['range_settings']['range_name'] = answers['range_name']

    print("> configuring attack_range environment")
    questions = [
        {
            'type': 'confirm',
            'message': 'should we build a windows domain controller',
            'name': 'windows_domain_controller',
            'default': True,
        },
        {
            'type': 'confirm',
            'message': 'should we build a windows server',
            'name': 'windows_server',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'should we build a windows client',
            'name': 'windows_client',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'should we build a kali linux machine for ad-hoc testing',
            'name': 'kali_machine',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'should we build zeek sensors',
            'name': 'zeek_sensor',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'should we build a phantom server',
            'name': 'phantom_server',
            'default': False,
        },
        {
            'type': 'input',
            'message': 'phantom community username (my.phantom.us), required for phantom server',
            'name': 'phantom_community_username',
            'when': lambda answers: answers['phantom_server'],
            'default': 'user',
        },
        {
            'type': 'input',
            'message': 'phantom community password (my.phantom.us), required for phantom server',
            'name': 'phantom_community_password',
            'when': lambda answers: answers['phantom_server'],
            'default': 'password',
        },
    ]
    answers = prompt(questions)
    enabled = lambda x : 1 if x else 0
    configuration._sections['environment']['phantom_server'] = enabled(answers['phantom_server'])
    if 'phantom_community_username' in answers:
        configuration._sections['environment']['phantom_community_username'] = answers['phantom_community_username']
    if 'phantom_community_password' in answers:
        configuration._sections['environment']['phantom_community_password'] = answers['phantom_community_password']
    configuration._sections['environment']['windows_domain_controller'] = enabled(answers['windows_domain_controller'])
    configuration._sections['environment']['windows_server'] = enabled(answers['windows_server'])
    configuration._sections['environment']['kali_machine'] = enabled(answers['kali_machine'])
    configuration._sections['environment']['windows_client'] = enabled(answers['windows_client'])
    configuration._sections['environment']['zeek_sensor'] = enabled(answers['zeek_sensor'])

    # write config file
    with open(attack_range_config, 'w') as configfile:
        configuration.write(configfile)
    print("> attack_range configuration file was written to: {0} .. run `python attack_range.py build` to create a new attack_range".format(Path(attack_range_config).resolve()))
    print("> setup has finished successfully ... exiting")
    sys.exit(0)
if __name__ == "__main__":
    main(sys.argv[1:])

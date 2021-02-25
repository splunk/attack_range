#!/usr/bin/python

'''
Helps configure your attack_range before using.
'''

from Crypto.PublicKey import RSA
from pathlib import Path
from PyInquirer import prompt, Separator
from botocore.config import Config
import sys
import argparse
import urllib.request
import configparser
import random
import string
import boto3
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

def create_key_pair_aws(client):
    # create new ssh key
    epoch_time = str(int(time.time()))
    ssh_key_name = getpass.getuser() + "-" + epoch_time[-5:] + ".key"
    # create ssh keys
    response = client.create_key_pair(KeyName=str(ssh_key_name)[:-4])
    with open(ssh_key_name, "w") as ssh_key:
        ssh_key.write(response['KeyMaterial'])
    os.chmod(ssh_key_name, 0o600)
    return ssh_key_name

def create_key_pair_azure():
    # create new ssh key
    epoch_time = str(int(time.time()))
    key = RSA.generate(2048)
    priv_key_name = getpass.getuser() + "-" + epoch_time[-5:] + ".key"
    pub_key_name = getpass.getuser() + "-" + epoch_time[-5:] + ".pub"
    with open(priv_key_name, 'wb') as content_file:
        os.chmod(priv_key_name, 0o600)
        content_file.write(key.exportKey('PEM'))
    pubkey = key.publickey()
    with open(pub_key_name, 'wb') as content_file:
        content_file.write(pubkey.exportKey('OpenSSH'))
    return priv_key_name, pub_key_name

def check_for_generated_keys(answers):
    keys = []
    for file in os.listdir("."):
        if file.endswith(".key"):
            keys.append(Path(file).resolve())
    if len(keys) > 0:
        return True
    return False

def get_generated_keys():
    priv_keys = []
    pub_keys = []
    for file in os.listdir("."):
        if file.endswith(".key"):
            priv_keys.append(Path(file).resolve())
        if file.endswith(".pub"):
            pub_keys.append(Path(file).resolve())
    if len(priv_keys) > 0:
        priv_key = priv_keys[0]
    else:
        priv_key = ''

    if len(pub_keys) > 0:
        pub_key = pub_keys[0]
    else:
        pub_key = ''

    return priv_key, pub_key

def check_reuse_keys(answers):
    if 'reuse_keys' in answers:
        if answers['reuse_keys']:
            return False
        else:
            return True
    else:
        return True

def new(config):
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
    else:
        aws_configured_region = ''
    configuration._sections['global']['cloud_provider'] = answers['cloud_provider']
    configuration._sections['global']['attack_range_password'] = answers['attack_range_password']
    if 'azure_subscription_id' in answers:
        configuration._sections['azure']['azure_subscription_id'] = answers['azure_subscription_id']
    else:
        configuration._sections['azure']['azure_subscription_id'] = 'xxxXXX'

    print("> configuring attack_range settings")

    # get external IP for default suggestion on whitelist question
    try:
        external_ip = urllib.request.urlopen('https://v4.ident.me').read().decode('utf8')
    except:
        print("WARNING, unable to determine the public ip")
        external_ip = ''

    # get the latest key generated
    priv_key, pub_key  = get_generated_keys()

    questions = [
        {   # reuse key pair?
            'type': 'confirm',
            'message': 'detected existing key in {0}, would you like to use it'.format(priv_key),
            'name': 'reuse_keys',
            'default': True,
            'when': check_for_generated_keys,
        },
        {   # new key pair?
            'type': 'confirm',
            'message': 'generate a new ssh key pair for this range',
            'name': 'new_key_pair',
            'default': True,
            'when': check_reuse_keys,
        },
    ]

    # check if we should generate a key pair
    answers = prompt(questions)
    if 'reuse_keys' in answers:
        if answers['reuse_keys']:
            priv_key_name = os.path.basename(os.path.normpath(priv_key))
            configuration._sections['range_settings']['key_name'] = str(priv_key_name)[:-4]
            configuration._sections['range_settings']['private_key_path'] = str(priv_key)
            configuration._sections['range_settings']['public_key_path'] = str(pub_key)
            print("> included ssh private key: {}".format(priv_key))

    if 'new_key_pair' in answers:
        if answers['new_key_pair']:
            # create new ssh key for aws
            if configuration._sections['global']['cloud_provider'] == "aws":
                new_key_name = create_key_pair_aws(aws_session.client('ec2', region_name=aws_configured_region))
                new_key_path = Path(new_key_name).resolve()
                configuration._sections['range_settings']['key_name'] = new_key_name[:-4]
                configuration._sections['range_settings']['private_key_path'] = str(new_key_path)
                configuration._sections['range_settings']['public_key_path'] = str(pub_key)
                print("> new aws ssh created: {}".format(new_key_path))
            elif configuration._sections['global']['cloud_provider'] == "azure":
                priv_key_name, pub_key_name = create_key_pair_azure()
                priv_key_path = Path(priv_key_name).resolve()
                pub_key_path = Path(pub_key_name).resolve()
                configuration._sections['range_settings']['key_name'] = priv_key_name[:-4]
                configuration._sections['range_settings']['private_key_path'] = str(priv_key_path)
                configuration._sections['range_settings']['public_key_path'] = str(pub_key_path)
                print("> new azure ssh pair created:\nprivate key: {0}\npublic key:{1}".format(priv_key_path, pub_key_path))
            else:
                print("ERROR, we do not support generating a key pair for the selected provider: {}".format(configuration._sections['global']['cloud_provider']))



    questions = [
        {
            # get api_key
            'type': 'input',
            'message': 'enter ssh key name',
            'name': 'key_name',
            'default': 'attack-range-key-pair',
            'when': lambda answers: configuration._sections['range_settings']['key_name'] == 'attack-range-key-pair',
        },
        {
            # get private_key_path
            'type': 'input',
            'message': 'enter private key path for machine access',
            'name': 'private_key_path',
            'default': "~/.ssh/id_rsa",
            'when': lambda answers: configuration._sections['range_settings']['key_name'] == 'attack-range-key-pair',
        },
        {
            # get public_key_path
            'type': 'input',
            'message': 'enter public key path for machine access',
            'name': 'public_key_path',
            'default': "~/.ssh/id_rsa.pub",
            'when': lambda answers: configuration._sections['range_settings']['public_key_path'] == '',
        },
        {
            # get region
            'type': 'input',
            'message': 'enter region to build in.',
            'name': 'region',
            'default': aws_configured_region,
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
    # manage keys first
    if 'key_name' in answers:
        configuration._sections['range_settings']['key_name'] = answers['key_name']
    else:
        print("> using ssh key name: {}".format(configuration._sections['range_settings']['key_name']))
    if 'private_key_path' in answers:
        configuration._sections['range_settings']['private_key_path'] = answers['private_key_path']
    else:
        print("> using ssh private key: {}".format(configuration._sections['range_settings']['private_key_path']))
    if 'public_key_path' in answers:
        configuration._sections['range_settings']['public_key_path'] = answers['public_key_path']
    else:
        print("> using ssh public key: {}".format(configuration._sections['range_settings']['public_key_path']))
    # get region
    if 'region' in answers:
        configuration._sections['range_settings']['region'] = answers['region']
    else:
        configuration._sections['range_settings']['region'] = 'us-west-2'
    # rest of configs
    configuration._sections['range_settings']['ip_whitelist'] = answers['ip_whitelist']
    configuration._sections['range_settings']['range_name'] = answers['range_name']

    print("> configuring attack_range environment")
    questions = [
        {
            'type': 'confirm',
            'message': 'shall we build a windows domain controller',
            'name': 'windows_domain_controller',
            'default': True,
        },
        {
            'type': 'confirm',
            'message': 'shall we build a windows server',
            'name': 'windows_server',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'shall we build a windows client',
            'name': 'windows_client',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'shall we build a kali linux machine for ad-hoc testing',
            'name': 'kali_machine',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'shall we build zeek sensors',
            'name': 'zeek_sensor',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'shall we build a phantom server',
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
        configuration._sections['phantom_settings']['phantom_community_username'] = answers['phantom_community_username']
    if 'phantom_community_password' in answers:
        configuration._sections['phantom_settings']['phantom_community_password'] = answers['phantom_community_password']

    if (enabled(answers['windows_domain_controller'])):
        configuration._sections['environment']['windows_domain_controller'] = enabled(answers['windows_domain_controller'])
    else:
        configuration._sections['environment']['windows_domain_controller'] = enabled(answers['windows_domain_controller'])
        configuration._sections['windows_server']['windows_server_join_domain'] = 0
        configuration._sections['windows_client']['windows_client_join_domain'] = 0

    configuration._sections['environment']['windows_server'] = enabled(answers['windows_server'])
    configuration._sections['environment']['kali_machine'] = enabled(answers['kali_machine'])
    configuration._sections['environment']['windows_client'] = enabled(answers['windows_client'])
    configuration._sections['environment']['zeek_sensor'] = enabled(answers['zeek_sensor'])

    # write config file
    with open(attack_range_config, 'w') as configfile:
        configuration.write(configfile)
    print("> configuration file was written to: {0}, run `python attack_range.py build` to create a new attack_range\nyou can also edit this file to configure advance parameters".format(Path(attack_range_config).resolve()))
    print("> setup has finished successfully ... exiting")
    sys.exit(0)

from Crypto.PublicKey import RSA
from pathlib import Path
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
import questionary
import os
import yaml


# need to be retrieved from config
VERSION = "3.0.0"


def get_random_password():
    """
    get_random_password function generates random password.
    :return: returns the generated password
    """
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


def create_key_pair_aws(region):
    """
    create_key_pair_aws function reates an ED25519 or 2048-bit RSA key pair with the specified name and in the specified PEM or PPK format. 
    Amazon EC2 stores the public key and displays the private key for you to save to a file.
    :param region: region
    :return: ssh key name
    """

    aws_session = boto3.Session()
    client = aws_session.client('ec2', region_name=region)

    # create new ssh key
    epoch_time = str(int(time.time()))
    ssh_key_name = getpass.getuser() + "-" + epoch_time[-5:] + ".key"
    # create ssh keys
    response = client.create_key_pair(KeyType='ed25519', KeyName=str(ssh_key_name)[:-4])
    with open(ssh_key_name, "w") as ssh_key:
        ssh_key.write(response['KeyMaterial'])
    os.chmod(ssh_key_name, 0o600)
    return ssh_key_name


def create_key_pair_azure():
    """
    create_key_pair_azure function creates public and private key for Azure.
    :return: private and public key name
    """
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
    """
    check_for_generated_keys function checks for the presence of .key file in the project directory.
    :return: Boolean output based on the existance of the .key file
    """
    keys = []
    for file in os.listdir("."):
        if file.endswith(".key"):
            keys.append(Path(file).resolve())
    if len(keys) > 0:
        return True
    return False


def get_generated_keys():
    """
    get_generated_keys function gets the .key & .pub files in the project directory.
    :return: private and public key file name
    """
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
    """
    check_reuse_keys function checks for key reuse.
    :return: boolean output
    """
    if 'reuse_keys' in answers:
        if answers['reuse_keys']:
            return False
        else:
            return True
    else:
        return True


def new(config):
    """
    new function creates a new configuration file based on the user input on the terminal.
    :param config: python dictionary having the configuration 
    :return: No return value
    """
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

        answers = questionary.prompt(questions)
        if answers['continue']:
            print("> continuing with attack_range configuration...")
        else:
            print(
                "> exiting, to create a unique configuration file in another location use the --config flag")
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

    configuration = dict()
    configuration['general'] = dict()

    questions = [
        {
            # get provider
            'type': 'select',
            'message': 'select cloud provider',
            'name': 'provider',
            'choices': ['aws','azure', 'local'],
            'default': 'aws'
        },
        {
            # get api_key
            'type': 'input',
            'message': 'enter azure subscription id',
            'name': 'azure_subscription_id',
            'when': lambda answers: answers['provider'] == 'azure',
        },
        {
            # get range password
            'type': 'input',
            'message': 'enter a master password for your attack_range',
            'name': 'attack_range_password',
            'default': get_random_password(),
        },
        {   # use packer
            'type': 'confirm',
            'message': 'do you want to use packer for prebuilt images?',
            'name': 'use_packer',
            'when': lambda answers: answers['provider'] != 'local',
        },
    ]

    answers = questionary.prompt(questions)
    if answers['provider'] == 'aws':
        aws_session = boto3.Session()
        if aws_session.region_name:
            aws_configured_region = aws_session.region_name
        else:
            print(
                "ERROR aws region not configured, please run `aws configure` to setup awscli")
            sys.exit(1)
    else:
        aws_configured_region = ''
    
    configuration['general']['cloud_provider'] = answers['provider']
    configuration[answers['provider']] = dict()
    configuration['general']['attack_range_password'] = answers['attack_range_password']
    
    if 'azure_subscription_id' in answers:
        configuration['azure']['subscription_id'] = answers['azure_subscription_id']

    if 'use_packer' in answers:
        if answers['use_packer']:
            configuration['general']['use_prebuilt_images_with_packer'] = '1'
        else:
            configuration['general']['use_prebuilt_images_with_packer'] = '0'

    print("> configuring attack_range settings")

    # get external IP for default suggestion on whitelist question
    try:
        external_ip = urllib.request.urlopen('https://v4.ident.me').read().decode('utf8')
    except:
        print("WARNING, unable to determine the public ip")
        external_ip = ''

    # get the latest key generated
    priv_key, pub_key = get_generated_keys()

    if configuration['general']['cloud_provider'] != 'local':
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
        answers = questionary.prompt(questions)
        if 'reuse_keys' in answers:
            if answers['reuse_keys']:
                priv_key_name = os.path.basename(os.path.normpath(priv_key))
                configuration['general']['key_name'] = str(priv_key_name)[:-4]
                if configuration['general']['cloud_provider'] == "azure":
                    configuration['azure']['private_key_path'] = str(priv_key)
                    configuration['azure']['public_key_path'] = str(pub_key)
                else:
                    configuration['aws']['private_key_path'] = str(priv_key)
                
                print("> included ssh private key: {}".format(priv_key))

        if 'new_key_pair' in answers:
            if answers['new_key_pair']:
                # create new ssh key for aws
                if configuration['general']['cloud_provider'] == "aws":
                    new_key_name = create_key_pair_aws(aws_configured_region)
                    new_key_path = Path(new_key_name).resolve()
                    configuration['general']['key_name'] = new_key_name[:-4]
                    configuration['aws']['private_key_path'] = str(new_key_path)
                    print("> new aws ssh created: {}".format(new_key_path))

                elif configuration['general']['cloud_provider'] == "azure":
                    priv_key_name, pub_key_name = create_key_pair_azure()
                    priv_key_path = Path(priv_key_name).resolve()
                    pub_key_path = Path(pub_key_name).resolve()
                    configuration['general']['key_name'] = priv_key_name[:-4]
                    configuration['azure']['private_key_path'] = str(priv_key_path)
                    configuration['azure']['public_key_path'] = str(pub_key_path)
                    print("> new azure ssh pair created:\nprivate key: {0}\npublic key:{1}".format(
                        priv_key_path, pub_key_path))
                else:
                    print("ERROR, we do not support generating a key pair for the selected provider: {}".format(
                        configuration['general']['cloud_provider']))


        questions = [
            {
                # get api_key
                'type': 'text',
                'message': 'enter ssh key name',
                'name': 'key_name',
                'default': 'attack-range-key-pair',
                'when': lambda answers: 'key_name' not in configuration['general'],
            },
            {
                # get private_key_path
                'type': 'text',
                'message': 'enter private key path for machine access',
                'name': 'private_key_path',
                'default': "~/.ssh/id_rsa",
                'when': lambda answers: 'key_name' not in configuration['general'],
            },
            {
                # get public_key_path
                'type': 'text',
                'message': 'enter public key path for machine access',
                'name': 'public_key_path',
                'default': "~/.ssh/id_rsa.pub",
                'when': lambda answers: ('key_name' not in configuration['general']) and (configuration['general']['cloud_provider'] == "azure"),
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
                'type': 'text',
                'message': 'enter public ips that are allowed to reach the attack_range.\nExample: {0}/32,0.0.0.0/0'.format(external_ip),
                'name': 'ip_whitelist',
                'default': external_ip + "/32"
            },
            {
                # get range name
                'type': 'text',
                'message': 'enter attack_range name, multiple can be build under different names in the same region',
                'name': 'attack_range_name',
                'default': "ar",
            },

        ]

        answers = questionary.prompt(questions)
        # manage keys first
        if 'key_name' in answers:
            configuration['general']['key_name'] =  answers['key_name']
        else:
            print("> using ssh key name: {}".format(
                configuration['general']['key_name']))
        if 'private_key_path' in answers:
            if configuration['general']['cloud_provider'] == "aws":
                configuration['aws']['private_key_path'] = answers['private_key_path']
            else:
                configuration['azure']['private_key_path'] = answers['private_key_path']
        if 'public_key_path' in answers:
            if configuration['general']['cloud_provider'] == "aws":
                configuration['aws']['public_key_path'] = answers['public_key_path']
            else:
                configuration['azure']['public_key_path'] = answers['public_key_path']

        # get region
        if 'region' in answers:
            if configuration['general']['cloud_provider'] == "aws":
                configuration['aws']['region'] = answers['region']
            else:
                configuration['azure']['location'] = answers['region']
        else:
            if configuration['general']['cloud_provider'] == "aws":
                configuration['aws']['region'] = 'eu-central-1'
            else:
                configuration['azure']['region'] = 'West Europe'
        
        # rest of configs
        configuration['general']['ip_whitelist'] = answers['ip_whitelist']
        configuration['general']['attack_range_name'] = answers['attack_range_name']

    print("> configuring attack_range environment")

    questions = [
        {
            'type': 'confirm',
            'message': 'shall we build a windows server',
            'name': 'windows_server_one',
            'default': True,
        },
        {
            'type': 'select',
            'message': 'which version should it be',
            'name': 'windows_server_one_version',
            'choices': ['2016', '2019'],
            'when': lambda answers: answers['windows_server_one'],
        },
        {
            'type': 'confirm',
            'message': 'should the windows server be a domain controller',
            'name': 'windows_server_one_dc',
            'default': False,
            'when': lambda answers: answers['windows_server_one'],
        },
        {
            'type': 'confirm',
            'message': 'should we install red team tools on the windows server',
            'name': 'windows_server_one_red_team_tools',
            'default': False,
            'when': lambda answers: answers['windows_server_one'],
        },
        {
            'type': 'confirm',
            'message': 'should we install badblood on the windows server, which will populate the domain with objects',
            'name': 'windows_server_one_bad_blood',
            'default': False,
            'when': lambda answers: answers['windows_server_one'] and answers['windows_server_one_dc'],
        },
    ]

    answers = questionary.prompt(questions)

    if answers['windows_server_one']:
        configuration['windows_servers'] = list()
        configuration['windows_servers'].append({
            'hostname': 'ar-win-1',
            'windows_image': 'windows-' + answers['windows_server_one_version'] + '-v' + VERSION.replace(".","-"),
        })
        if answers['windows_server_one_dc']:
            configuration['windows_servers'][0]['create_domain'] = '1'
            configuration['windows_servers'][0]['hostname'] = 'ar-win-dc'
        if answers['windows_server_one_red_team_tools']:
            configuration['windows_servers'][0]['install_red_team_tools'] = '1'
        if 'windows_server_one_bad_blood' in answers:
            if answers['windows_server_one_bad_blood']:
                configuration['windows_servers'][0]['bad_blood'] = '1'        

        questions = [
            {
                'type': 'confirm',
                'message': 'shall we build another windows server',
                'name': 'windows_server_two',
                'default': False,
            },
            {
                'type': 'select',
                'message': 'which version should it be',
                'name': 'windows_server_two_version',
                'choices': ['2016', '2019'],
                'when': lambda answers: answers['windows_server_two'],
            },
            {
                'type': 'confirm',
                'message': 'should the windows server join the domain',
                'name': 'windows_server_two_join_dc',
                'default': False,
                'when': lambda answers: answers['windows_server_two'] and 'create_domain' in configuration['windows_servers'][0],
            },
            {
                'type': 'confirm',
                'message': 'should we install red team tools on the windows server',
                'name': 'windows_server_two_red_team_tools',
                'default': False,
                'when': lambda answers: answers['windows_server_two'],
            },
        ]

        answers = questionary.prompt(questions)

        if answers['windows_server_two']:
            configuration['windows_servers'].append({
                'hostname': 'ar-win-2',
                'windows_image': 'windows-' + answers['windows_server_two_version'] + '-v' + VERSION.replace(".","-"),
            })
            if 'windows_server_two_join_dc' in answers:    
                if answers['windows_server_two_join_dc']:
                    configuration['windows_servers'][1]['join_domain'] = '1'              
            if answers['windows_server_two_red_team_tools']:
                configuration['windows_servers'][1]['install_red_team_tools'] = '1'  


    questions = [
        {
            'type': 'confirm',
            'message': 'shall we build a linux server',
            'name': 'linux_server',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'shall we build a kali linux machine',
            'name': 'kali_machine',
            'default': False,
            'when': lambda answers: configuration['general']['cloud_provider'] == "aws",
        },
        {
            'type': 'confirm',
            'message': 'shall we build nginx plus web proxy',
            'name': 'nginx_web_proxy',
            'default': False,
            'when': lambda answers: configuration['general']['cloud_provider'] == "aws",
        },
        {
            'type': 'confirm',
            'message': 'shall we include Splunk SOAR',
            'name': 'phantom',
            'default': False,
        },
        {
            'type': 'text',
            'message': 'Download the Splunk SOAR unpriv installer and save it in the apps folder. What is the name of the file?',
            'name': 'phantom_installer',
            'when': lambda answers: answers['phantom'],
        }
    ]

    answers = questionary.prompt(questions)

    if answers['linux_server']:
        configuration['linux_servers'] = list()
        configuration['linux_servers'].append(
            {
                'hostname': 'ar-linux',
            }
        )
    
    if configuration['general']['cloud_provider'] == "aws":
        if answers['kali_machine']:
            configuration['kali_server'] = dict()
            configuration['kali_server']['kali_server'] = '1'

        if answers['nginx_web_proxy']:
            configuration['nginx_server'] = dict()
            configuration['nginx_server']['nginx_server'] = '1'

    if answers['phantom']:
        configuration['phantom_server'] = dict()
        configuration['phantom_server']['phantom_server'] = '1'

    if 'phantom_installer' in answers:
        configuration['phantom_server']['phantom_app'] = answers['phantom_installer']


    # write config file
    with open(attack_range_config, 'w') as outfile:
        yaml.dump(configuration, outfile, default_flow_style=False, sort_keys=False)

    print("> configuration file was written to: {0}, run `python attack_range.py build` to create a new attack_range\nyou can also edit this file to configure advance parameters".format(
        Path(attack_range_config).resolve()))
    print("> setup has finished successfully ... exiting")
    sys.exit(0)
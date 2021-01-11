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


CONFIG_TEMPLATE = 'attack_range.conf.template'

def load_config_template(CONFIG_TEMPLATE):
    """Provided a config file path and a collections of type dict,
    will return that collections with all the settings in it"""
    settings = {}
    config = configparser.RawConfigParser()
    config.read(CONFIG_TEMPLATE)
    for section in config.sections():
        for key in config[section]:
            try:
                settings[key] = config.get(section, key)
            except Exception as e:
                print(
                    "ERROR - reading configuration template: {0} at {0} failed with error {1}".format(CONFIG_TEMPLATE, e))
                sys.exit(1)
    return config

def get_random_password():
    random_source = string.ascii_letters + string.digits + string.punctuation
    password = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)
    password += random.choice(string.punctuation)

    for i in range(6):
        password += random.choice(random_source)

    password_list = list(password)
    random.SystemRandom().shuffle(password_list)
    password = ''.join(password_list)
    return password

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
            print("continuing with attack_range configuration...")
        else:
            print("exiting, to create a unique configuration file in another location use the --config flag")
            parser.print_help()
            sys.exit(0)
        print(answers)  # use the answers as input for your app
        configpath = str(attack_range_config)

    print("""
        /-----^\\
       /==     |
   +-o/   ==B) |
      /__/-----|
         =====
         ( \ \ \\
          \ \ \ \\
           ( ) ( )
           / /  \ \\
         / /     | |
         /        |
       _^^oo    _^^oo
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
            # get range password
            'type': 'input',
            'message': 'enter a master password for your attack_range',
            'name': 'attack_range_password',
            'default': get_random_password(),
        },
        {
            # get api_key
            'type': 'input',
            'message': 'enter azure subscription id',
            'name': 'azure_subscription_id',
            'when': lambda answers: answers['cloud_provider'] == 'azure',
        },
    ]
    answers = prompt(questions)
    configuration._sections['global']['cloud_provider'] = answers['cloud_provider']
    configuration._sections['global']['attack_range_password'] = answers['attack_range_password']
    if 'azure_subscription_id' in answers:
        configuration._sections['azure']['azure_subscription_id'] = answers['azure_subscription_id']
    else:
        configuration._sections['azure']['azure_subscription_id'] = 'xxxXXX'

    print("configuring attack_range settings")
    # get external IP for default suggestion on whitelist question
    external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
    questions = [

        {
            # get api_key
            'type': 'input',
            'message': 'enter ssh key name',
            'name': 'key_name',
        },
        {
            # get whitelist
            'type': 'input',
            'message': 'enter public ips that are allowed to reach the attack_range.\nExample: {0}/32,0.0.0.0/0'.format(external_ip),
            'name': 'ip_whitelist',
            'default': external_ip + "/32"
        },
        {
            # get private_key_path
            'type': 'input',
            'message': 'enter private key path for machine access',
            'name': 'private_key_path',
            'default': "~/.ssh/id_rsa"
        },
        {
            # get public_key_path
            'type': 'input',
            'message': 'enter public key path for machine access',
            'name': 'public_key_path',
            'default': "~/.ssh/id_rsa.pub",
            'when': lambda  answers: configuration._sections['global']['cloud_provider'] == 'azure',
        },
        {
            # get region
            'type': 'input',
            'message': 'enter aws region to build in.',
            'name': 'region',
            'default': "us-west-2",
            'when': lambda  answers: configuration._sections['global']['cloud_provider'] == 'aws',
        },
        {
            # get range name
            'type': 'input',
            'message': 'enter attack_range name, multiple can be build on the same region under different names.',
            'name': 'range_name',
            'default': "default",
        },

    ]
    answers = prompt(questions)
    configuration._sections['range_settings']['key_name'] = answers['key_name']
    configuration._sections['range_settings']['ip_whitelist'] = answers['ip_whitelist']
    configuration._sections['range_settings']['private_key_path'] = answers['private_key_path']

    if 'public_key_path' in answers:
        configuration._sections['range_settings']['public_key_path'] = answers['public_key_path']
    else:
        configuration._sections['range_settings']['public_key_path'] = '~/.ssh/id_rsa.pub'

    if 'region' in answers:
        configuration._sections['range_settings']['region'] = answers['region']
    else:
        configuration._sections['range_settings']['region'] = 'us-west-2'
    configuration._sections['range_settings']['range_name'] = answers['range_name']

    print("configuring attack_range environment")
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
            'message': 'should we build a phantom server',
            'name': 'phantom_server',
            'default': False,
        },
        {
            'type': 'confirm',
            'message': 'should we build zeek sensors',
            'name': 'zeek_sensor',
            'default': False,
        },
    ]
    answers = prompt(questions)
    print(answers)
    configuration._sections['environment']['phantom_server'] = answers['phantom_server']
    configuration._sections['environment']['windows_domain_controller'] = answers['windows_domain_controller']
    configuration._sections['environment']['windows_server'] = answers['windows_server']
    configuration._sections['environment']['kali_machine'] = answers['kali_machine']
    configuration._sections['environment']['windows_client'] = answers['windows_client']
    configuration._sections['environment']['zeek_sensor'] = answers['zeek_sensor']
    
    # write config file
    with open(attack_range_config, 'w') as configfile:
        configuration.write(configfile)

if __name__ == "__main__":
    main(sys.argv[1:])

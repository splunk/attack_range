#!/usr/bin/python

'''
Helps configure your attack range before using.
'''

import sys
from pathlib import Path
import argparse
import urllib.request
from PyInquirer import prompt, Separator
import configparser


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
    return settings

def main(args):
    # grab args
    parser = argparse.ArgumentParser(
        description="Use `attack_range.py action -h` to get help with any Attack Range action")
    parser.add_argument("-c", "--config", required=False, default="attack_range.conf",
                        help="path to the configuration file of the attack range")
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
            # get api_key
            'type': 'input',
            'message': 'enter azure subscription id',
            'name': 'azure_subscription_id',
            'when': lambda answers: answers['cloud_provider'] == 'azure',
        },
    ]
    answers = prompt(questions)
    configuration['cloud_provider'] = answers['cloud_provider']
    if 'azure_subscription_id' in answers:
        configuration['azure_subscription_id'] = answers['azure_subscription_id']
    else:
        configuration['azure_subscription_id'] = 'xxxXXX'

    print("configuring range settings")
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
            'when': lambda  answers: configuration['cloud_provider'] == 'azure',
        },
        {
            # get region
            'type': 'input',
            'message': 'enter aws region to build in.',
            'name': 'region',
            'default': "us-west-2",
            'when': lambda  answers: configuration['cloud_provider'] == 'aws',
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
    configuration['key_name'] = answers['key_name']
    configuration['ip_whitelist'] = answers['ip_whitelist']
    configuration['private_key_path'] = answers['private_key_path']

    if 'public_key_path' in answers:
        configuration['public_key_path'] = answers['public_key_path']
    else:
        configuration['public_key_path'] = '~/.ssh/id_rsa.pub'

    if 'region' in answers:
        configuration['region'] = answers['region']
    else:
        configuration['region'] = 'us-west-2'
    configuration['range_name'] = answers['range_name']
    print(configuration)  # use the answers as input for your app

    #with open(attack_range_config, 'w') as configfile:
    #    configuration.write(configfile)

if __name__ == "__main__":
    main(sys.argv[1:])

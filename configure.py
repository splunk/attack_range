#!/usr/bin/python

'''
Helps configure your attack range before using.
'''

import sys
from pathlib import Path
import argparse
import urllib.request
from PyInquirer import prompt, Separator



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
    else:
        print("ERROR: attack_range failed to find a config file at {0} or {1}..exiting".format(attack_range_config))
        sys.exit(1)

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

    configuration = dict()
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
            # get api_key
            'type': 'input',
            'message': 'enter aws ssh key name',
            'name': '',
            'when': lambda answers: answers['cloud_provider'] == 'azure',
        },
    ]
    answers = prompt(questions)
    configuration['provider'] = answers

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
            # get api_key
            'type': 'input',
            'message': 'enter public ips that are allowed to reach the attack_range.\nExample: {0}/32,0.0.0.0/0'.format(external_ip),
            'name': 'ip_whitelist',
            'default': external_ip + "/32"
        },
    ]
    answers = prompt(questions)
    configuration['range_settings'] = answers
    print(configuration)  # use the answers as input for your app

if __name__ == "__main__":
    main(sys.argv[1:])

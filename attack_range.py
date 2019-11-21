import argparse
import re
import vagrant
import ansible_runner
import subprocess
import boto3
from python_terraform import *
from modules import logger, parseconfig
from pathlib import Path

# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

VERSION = 1


# could be improved by directly use extra-vars
def config_simulation(simulation_engine, simulation_technique, log):

    # Read in the ansible vars file
    with open('ansible/vars/vars.yml.default', 'r') as file:
        ansiblevars = file.read()

    # now set the simulation engine and mitre techniques to run
    if simulation_engine == "atomic_red_team":
        ansiblevars = re.sub(r'install_art: \w+', 'install_art: true', ansiblevars, re.M)
        log.info("execution simulation using engine: {0}".format(simulation_engine))

    if simulation_technique[0] != '' or len(simulation_technique) > 1:
        technique = "art_run_technique: " + str(simulation_technique)
        ansiblevars = re.sub(r'art_run_technique: .+', technique, ansiblevars, re.M)
        ansiblevars = re.sub(r'art_run_all_test: \w+', 'art_run_all_test: false', ansiblevars, re.M)
        log.info("executing specific ATT&CK technique ID: {0}".format(simulation_technique))
    else:
        ansiblevars = re.sub(r'art_run_all_test: \w+', 'art_run_all_test: true', ansiblevars, re.M)
        log.info("executing ALL Atomic Red Team ATT&CK techniques see: https://github.com/redcanaryco/atomic-red-team/tree/master/atomics".format(
            simulation_technique))

    # Write the file out again
    with open('ansible/vars/vars.yml', 'w') as file:
        file.write(ansiblevars)


def run_simulation(mode, simulation_engine, simulation_techniques, target, log):

    if mode == "terraform":
        with open('ansible/inventory/hosts', 'r') as file:
            hosts_file = file.read()
        hosts_file = hosts_file.replace('PUBLICIP', target)
        with open('ansible/inventory/hosts', 'w') as file:
            file.write(hosts_file)


    # execute atomic red team simulation
    if simulation_engine == "atomic_red_team":
        r = ansible_runner.run(private_data_dir='.attack_range/',
                               inventory=os.path.dirname(os.path.realpath(
                                   __file__)) + '/ansible/inventory/hosts',
                               roles_path="../roles",
                               playbook=os.path.dirname(os.path.realpath(__file__)) + '/ansible/playbooks/atomic_red_team.yml',
                               verbosity=0)

        if r.status == "successful":
            log.info("successfully executed technique ID {0} against target: {1}".format(simulation_techniques, target))
        else:
            log.error("failed to executed technique ID {0} against target: {1}".format(simulation_techniques, target))
            sys.exit(1)


def prep_ansible(settings):
    # prep ansible for configuration
    # Read in the ansible vars file
    with open('ansible/vars/vars.yml.default', 'r') as file:
        ansiblevars = file.read()

    # Replace the ansible variables
    ansiblevars = re.sub(r'domain_admin_password: .+', 'domain_admin_password: ' + str(settings['win_password']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_pass: .+', 'splunk_pass: ' + str(settings['splunk_admin_password']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r's3_bucket_url: .+', 's3_bucket_url: ' + str(settings['s3_bucket_url']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_windows_ta: .+', 'splunk_windows_ta: ' + str(settings['splunk_windows_ta']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_sysmon_ta: .+', 'splunk_sysmon_ta: ' + str(settings['splunk_sysmon_ta']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_stream_ta: .+', 'splunk_stream_ta: ' + str(settings['splunk_stream_ta']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_stream_app: .+', 'splunk_stream_app: ' + str(settings['splunk_stream_app']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_cim_app: .+', 'splunk_cim_app: ' + str(settings['splunk_cim_app']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_escu_app: .+', 'splunk_escu_app: ' + str(settings['splunk_escu_app']),
                         ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_url: .+', 'splunk_url: ' + str(settings['splunk_url']),
                             ansiblevars, re.M)
    ansiblevars = re.sub(r'splunk_binary: .+', 'splunk_binary: ' + str(settings['splunk_binary']),
                             ansiblevars, re.M)

    # Write the file out again
    with open('ansible/vars/vars.yml', 'w') as file:
        file.write(ansiblevars)


    with open('ansible/inventory/hosts.default', 'r') as file:
        hosts_file = file.read()


    if mode == "vagrant":
        hosts_file = re.sub(r'ansible_ssh_port=.+', 'ansible_ssh_port=5985',
                                         hosts_file, re.M)
        hosts_file = re.sub(r'ansible_ssh_user=.+', 'ansible_ssh_user=vagrant',
                                         hosts_file, re.M)
        hosts_file = re.sub(r'ansible_ssh_pass=.+', 'ansible_ssh_pass=vagrant',
                                         hosts_file, re.M)
        hosts_file = hosts_file.replace('PUBLICIP', '127.0.0.1')
    else:
        hosts_file = re.sub(r'ansible_ssh_port=.+', 'ansible_ssh_port=5986',
                                         hosts_file, re.M)
        hosts_file = re.sub(r'ansible_ssh_user=.+', 'ansible_ssh_user=Administrator',
                                         hosts_file, re.M)
        hosts_file = re.sub(r'ansible_ssh_pass=.+', 'ansible_ssh_pass=' + str(settings['win_password']),
                                         hosts_file, re.M)


    # write hosts file to run from
    with open('ansible/inventory/hosts', 'w') as file:
        file.write(hosts_file)



def prep_terraform(settings):
    # prep terraform for configuration
    # Read in the ansible vars file
    with open('terraform/terraform.tfvars', 'r') as file:
        terraformvars = file.read()

    # Replace the ansible variables
    terraformvars = re.sub(r'key_name = .+', 'key_name = "' + str(settings['key_name']) + '"', terraformvars, re.M)
    terraformvars = re.sub(r'ip_whitelist = .+', 'ip_whitelist = ' + str(settings['ip_whitelist']),
                         terraformvars, re.M)
    terraformvars = re.sub(r'win_password = .+', 'win_password = "' + str(settings['win_password']) + '"',
                         terraformvars, re.M)
    terraformvars = re.sub(r'private_key_path = .+', 'private_key_path = "' + str(settings['private_key_path']) + '"',
                         terraformvars, re.M)
    # Write the file out again
    with open('terraform/terraform.tfvars', 'w') as file:
        file.write(terraformvars)


def vagrant_mode(action, log):

    vagrantfile = 'vagrant/'

    if action == "build":
        log.info("building splunk-server and windows10 workstation boxes WARNING MAKE SURE YOU HAVE 8GB OF RAM free otherwise you will have a bad time")
        log.info("[action] > build\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.up(provision=True)
        log.info("attack_range has been built using vagrant successfully")

    if action == "destroy":
        log.info("[action] > destroy\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.destroy()
        log.info("attack_range has been destroy using vagrant successfully")

    if action == "stop":
        print("[action] > stop\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.halt()

    if action == "resume":
        print("[action] > resume\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.up()


def attack_simulation(mode, target, simulation_engine, simulation_techniques, log):
    if mode == 'vagrant':
        v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False)
        status = v1.status()
        # Check if target exist and if it is running
        check_targets_running_vagrant(target, log)
        config_simulation(simulation_engine, simulation_techniques, log)
        run_simulation('vagrant', simulation_engine, simulation_techniques, target, log)

    if mode == 'terraform':
        target_IP = check_targets_running_terraform(target, log)
        config_simulation(simulation_engine, simulation_techniques, log)
        run_simulation('terraform', simulation_engine, simulation_techniques, target_IP, log)


def check_targets_running_terraform(target, log):
    with open('terraform/terraform.tfvars', 'r') as file:
        terraformvars = file.read()

    pattern = 'key_name = \"([^\"]*)'
    a = re.search(pattern, terraformvars)
    client = boto3.client('ec2')
    response = client.describe_instances(
        Filters=[
            {
                'Name': "tag:Name",
                'Values': [target]
            },
            {
                'Name': "key-name",
                'Values': [a.group(1)]
            }
        ]
    )

    if len(response['Reservations']) == 0:
        log.error(target + ' not found as AWS EC2 instance.')
        sys.exit(1)

    # iterate through reservations and instances
    found_running_instance = False
    for reservation in response['Reservations']:

        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running':
                found_running_instance = True
                return instance['NetworkInterfaces'][0]['Association']['PublicIp']

    if not found_running_instance:
        log.error(target + ' not running.')
        sys.exit(1)


def check_targets_running_vagrant(target, log):
    v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False)
    status = v1.status()

    found_box = False
    for stat in status:
        if stat.name == target:
            found_box = True
            if not (stat.state == 'running'):
                log.error(target + ' not running.')
                sys.exit(1)
            break
    if not found_box:
        log.error(target + ' not found as vagrant box.')
        sys.exit(1)



def terraform_mode(action, log):
    if action == "build":
        log.info("[action] > build\n")
        t = Terraform(working_dir='terraform')
        return_code, stdout, stderr = t.apply(
            capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        log.info("attack_range has been built using terraform successfully")

    if action == "destroy":
        log.info("[action] > destroy\n")
        t = Terraform(working_dir='terraform')
        return_code, stdout, stderr = t.destroy(capture_output='yes', no_color=IsNotFlagged)
        log.info("attack_range has been destroy using terraform successfully")

    if action == "stop" or action == "resume":
        instances, key_name = find_terraform_instances()
        change_terraform_state(instances, action, key_name, log)


def change_terraform_state(instances, action, key_name, log):
    client = boto3.client('ec2')
    # iterate through reservations and instances
    found_instance = False
    for instance in instances:
        if action == 'stop':
            if instance['State']['Name'] == 'running':
                found_instance = True
                response = client.stop_instances(
                    InstanceIds=[instance['InstanceId']]
                )
                log.info('Successfully stopped instance with ID ' +
                      instance['InstanceId'] + ' .')
        else:
            if instance['State']['Name'] == 'stopped':
                found_instance = True
                response = client.start_instances(
                    InstanceIds=[instance['InstanceId']]
                )
                log.info('Successfully started instance with ID ' + instance['InstanceId'] + ' .')

    if not found_instance:
        sys.exit('ERROR: No AWS EC2 instances with the key_name ' + key_name + ' found.')


def find_terraform_instances():
    with open('terraform/terraform.tfvars', 'r') as file:
        terraformvars = file.read()

    pattern = 'key_name = \"([^\"]*)'
    a = re.search(pattern, terraformvars)

    client = boto3.client('ec2')
    response = client.describe_instances(
        Filters=[
            {
                'Name': "key-name",
                'Values': [a.group(1)]
            }
        ]
    )
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            str = instance['Tags'][0]['Value']
            if str.startswith('attack-range'):
                instances.append(instance)

    return instances, a.group(1)


if __name__ == "__main__":
    # grab arguments
    parser = argparse.ArgumentParser(
        description="starts a attack range ready to collect attack data into splunk")
    parser.add_argument("-m", "--mode", required=True, default="terraform", choices=['vagrant', 'terraform'],
                        help="mode of operation, terraform/vagrant, please see configuration for each at: https://github.com/splunk/attack_range")
    parser.add_argument("-a", "--action", required=True, default="build", choices=['build', 'destroy', 'simulate', 'stop', 'resume'],
                        help="action to take on the range, defaults to \"build\", build/destroy/simulate/stop/resume allowed")
    parser.add_argument("-t", "--target", required=False,
                        help="target for attack simulation. For mode vagrant use name of the vbox. For mode terraform use the name of the aws EC2 name")
    parser.add_argument("-st", "--simulation_technique", required=False, type=str, default="",
                        help="comma delimited list of MITRE ATT&CK technique ID to simulate in the attack_range, example: T1117, T1118, requires --simulation flag")
    parser.add_argument("-c", "--config", required=False, default="attack_range.conf",
                        help="path to the configuration file of the attack range")
    parser.add_argument("-v", "--version", required=False,
                        help="shows current attack_range version")

    # parse them
    args = parser.parse_args()
    ARG_VERSION = args.version
    mode = args.mode
    action = args.action
    target = args.target
    config = args.config
    simulation_techniques = [str(item) for item in args.simulation_technique.split(',')]

    print("""
starting program loaded for B1 battle droid
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

    # parse config
    attack_range_config = Path(config)
    if attack_range_config.is_file():
        print("attack_range is using config at path {0}".format(attack_range_config))
        configpath = str(attack_range_config)
    else:
        print("attack_range failed to find a config file at {0} or {1}..exiting".format(attack_range_config))
        sys.exit(1)

    # Parse config
    parse = parseconfig.parser()
    settings = parse.load_conf(configpath)

    log = logger.setup_logging(settings['log_path'], settings['log_level'])
    log.info("INIT - Attack Range v" + str(VERSION))

    if ARG_VERSION:
        log.info("version: {0}".format(VERSION))
        sys.exit(1)


    # lets give CLI priority over config file for pre-configured techniques
    if simulation_techniques[0] != '' or len(simulation_techniques) > 1:
        pass
    else:
        simulation_techniques = settings['simulation_technique']


    # lets prep our config files base on provided settings
    prep_ansible(settings)

    if mode == "terraform":
        prep_terraform(settings)


    # to do: define which arguments are needed for build and which for simulate

    # lets process modes
    if mode == "vagrant":
        log.info("[mode] > vagrant")
        if action == "build" or action == "destroy" or action == "stop" or action == "resume":
            vagrant_mode(action, log)
        else:
            attack_simulation('vagrant', target, settings['simulation_engine'], simulation_techniques, log)

    elif mode == "terraform":
        log.info("[mode] > terraform ")
        if action == "build" or action == "destroy" or action == "stop" or action == "resume":
            terraform_mode(action, log)
        else:
            attack_simulation('terraform', target, settings['simulation_engine'], simulation_techniques, log)

    else:
        log.error("incorrect mode, please set flag --mode to \"terraform\" or \"vagrant\"")
        sys.exit(1)

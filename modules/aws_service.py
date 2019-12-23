import sys
import re
import boto3
from python_terraform import *



def get_instance_by_name(ec2_name, log):
    instances = get_all_instances()
    for instance in instances:
        str = instance['Tags'][0]['Value']
        if str == ec2_name:
            return instance


def get_all_instances():
    key_name = get_key_name()
    client = boto3.client('ec2')
    response = client.describe_instances(
        Filters=[
            {
                'Name': "key-name",
                'Values': [key_name]
            }
        ]
    )
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            str = instance['Tags'][0]['Value']
            if str.startswith('attack-range') and instance['State']['Name']!='terminated':
                instances.append(instance)

    return instances

#instance['NetworkInterfaces'][0]['Association']['PublicIp']


def check_ec2_instance_state(ec2_name, state):
    instance = get_instance_by_name(ec2_name)

    if not instance:
        log.error(ec2_name + ' not found as AWS EC2 instance.')
        sys.exit(1)

    return (instance['State']['Name'] == state)


def change_ec2_state(instances, new_state, log):

    client = boto3.client('ec2')

    if len(instances) == 0:
        log.error(ec2_name + ' not found as AWS EC2 instance.')
        sys.exit(1)

    if new_state == 'stopped':
        for instance in instances:
            if instance['State']['Name'] == 'running':
                response = client.stop_instances(
                    InstanceIds=[instance['InstanceId']]
                )
                log.info('Successfully stopped instance with ID ' +
                      instance['InstanceId'] + ' .')

    elif new_state == 'running':
        for instance in instances:
            if instance['State']['Name'] == 'stopped':
                response = client.start_instances(
                    InstanceIds=[instance['InstanceId']]
                )
                log.info('Successfully started instance with ID ' + instance['InstanceId'] + ' .')


def get_key_name():
    with open('terraform/terraform.tfvars', 'r') as file:
        terraformvars = file.read()

    pattern = 'key_name = \"([^\"]*)'
    a = re.search(pattern, terraformvars)

    return a.group(1)

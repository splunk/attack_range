import sys
import re
import boto3
from botocore.exceptions import ClientError
import uuid
import time
import yaml
import os

def get_instance_by_name(ec2_name, config):
    """
    get_instance_by_name function gets the running instance by ec2 name.

    :param ec2_name: ec2 name
    :param config: python dictionary having the configuration    
    :return: returns the running instance by name
    """
    instances = get_all_instances(config)
    for instance in instances:
        str = instance['Tags'][0]['Value']
        if str == ec2_name:
            return instance

def get_single_instance_public_ip(ec2_name, config):
    """
    get_single_instance_public_ip function gets the IP address of the running instance by ec2 name.

    :param ec2_name: ec2 name
    :param config: python dictionary having the configuration    
    :return: returns the IP address
    """
    instance = get_instance_by_name(ec2_name, config)
    return instance['NetworkInterfaces'][0]['Association']['PublicIp']


def get_all_instances(config):
    """
    get_all_instances function gets all the non-terminated AWS instances using boto3.

    :param config: python dictionary having the configuration
    :return: running instances
    """
    key_name = config['key_name']
    region = config['region']
    client = boto3.client('ec2', region_name=region)
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
            if instance['State']['Name']!='terminated':
                if len(instance['Tags']) > 0:
                    str = instance['Tags'][0]['Value']
                    if (config['range_name'] in str) and (config['key_name'] in str):
                        instances.append(instance)

    return instances


def get_splunk_instance_ip(config):
    """
    get_splunk_instance_ip function gets the IP address of the running splunk instance.

    :param config: python dictionary having the configuration.    
    :return: returns the IP address of the splunk instance.
    """
    all_instances = get_all_instances(config)
    for instance in all_instances:
        instance_tag = 'ar-splunk-' + config['range_name'] + '-' + config['key_name']
        if instance['Tags'][0]['Value'] == instance_tag:
            return instance['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['Association']['PublicIp']


def check_ec2_instance_state(ec2_name, state, log, config):
    """
    check_ec2_instance_state function checks whether the ec2 instance is having the particular state.

    :param ec2_name: ec2 name
    :param state: state to check the ec2 instance against
    :param log: logger object for logging
    :param config: python dictionary having the configuration 
    :return: returns boolean stating whether the state is same as required state      
    """
    instance = get_instance_by_name(ec2_name, config)

    if not instance:
        log.error(ec2_name + ' not found as AWS EC2 instance.')
        sys.exit(1)

    return (instance['State']['Name'] == state)


def change_ec2_state(instances, new_state, log, config):
    """
    change_ec2_state functions change the state of the instances on AWS.

    :param instances: list of instances
    :param new_state: The new state for the instances
    :param log: logger object for logging
    :param config: python dictionary having the configuration 
    :return: No return value
    """
    region = config['region']
    client = boto3.client('ec2', region_name=region)

    if len(instances) == 0:
        log.error('No instance passed.')
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


# def upload_file_s3_bucket(file_name, results, test_file, isArchive):
#     region = config['region']
#     s3_client = boto3.client('s3', region_name=region)
#     if isArchive:
#         response = s3_client.upload_file(file_name, 'attack-range-attack-data', str(test_file['simulation_technique'] + '/attack_data.tar.gz'))
#     else:
#         response = s3_client.upload_file(file_name, 'attack-range-attack-data', str(test_file['simulation_technique'] + '/attack_data.json'))
#
#     with open('tmp/test_results.yml', 'w') as f:
#         yaml.dump(results, f)
#     response2 = s3_client.upload_file('tmp/test_results.yml', 'attack-range-automated-testing', str(test_file['simulation_technique'] + '/test_results.yml'))
#     os.remove('tmp/test_results.yml')

def upload_file_s3_bucket(s3_bucket, file_path, S3_file_path, config):
    """
    upload_file_s3_bucket function upload file to s3 bucket.
    :param s3_bucket: s3 bucket to upload the file
    :param file_path: file path of the file
    :param S3_file_path: S3_file_path
    :param config: python dictionary having the configuration 
    :return: No return value
    """
    region = config['region']
    s3_client = boto3.client('s3', region_name=region)
    response = s3_client.upload_file(file_path, s3_bucket, S3_file_path)


def upload_test_results_s3_bucket(s3_bucket, test_file, test_result_file_path, config):
    """
    upload_file_s3_bucket function upload file to s3 bucket.
    :param s3_bucket: s3 bucket to upload the file
    :param file_path: file path of the file
    :param test_result_file_path: test_result_file_path
    :param config: python dictionary having the configuration 
    :return: No return value
    """
    region = config['region']
    s3_client = boto3.client('s3', region_name=region)
    response = s3_client.upload_file(test_result_file_path, s3_bucket, str(test_file['simulation_technique'] + '/test_results.yml'))

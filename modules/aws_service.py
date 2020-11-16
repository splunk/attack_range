import sys
import re
import boto3
from botocore.exceptions import ClientError
import uuid
import time
import yaml
import os

def get_instance_by_name(ec2_name, config):
    instances = get_all_instances(config)
    for instance in instances:
        str = instance['Tags'][0]['Value']
        if str == ec2_name:
            return instance

def get_single_instance_public_ip(ec2_name, config):
    instance = get_instance_by_name(ec2_name, config)
    return instance['NetworkInterfaces'][0]['Association']['PublicIp']


def get_all_instances(config):
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
    all_instances = get_all_instances(config)
    for instance in all_instances:
        instance_tag = 'ar-splunk-' + config['range_name'] + '-' + config['key_name']
        if instance['Tags'][0]['Value'] == instance_tag:
            return instance['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['Association']['PublicIp']


def check_ec2_instance_state(ec2_name, state, config):
    instance = get_instance_by_name(ec2_name, config)

    if not instance:
        log.error(ec2_name + ' not found as AWS EC2 instance.')
        sys.exit(1)

    return (instance['State']['Name'] == state)


def change_ec2_state(instances, new_state, log, config):
    region = config['region']
    client = boto3.client('ec2', region_name=region)

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
    region = config['region']
    s3_client = boto3.client('s3', region_name=region)
    response = s3_client.upload_file(file_path, s3_bucket, S3_file_path)


def upload_test_results_s3_bucket(s3_bucket, test_file, test_result_file_path, config):
    region = config['region']
    s3_client = boto3.client('s3', region_name=region)
    response = s3_client.upload_file(test_result_file_path, s3_bucket, str(test_file['simulation_technique'] + '/test_results.yml'))

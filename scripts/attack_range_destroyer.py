import os
import sys
import boto3

from datetime import datetime, timezone, timedelta

DAYS_TO_STOP = 7
DAYS_TO_TERMINATE = 30


def main(args):
    # list all attack ranges in all regions which are running
    instances = get_instances()
    change_instance_state(instances)

def get_all_instances_in_region(region):
    client = boto3.client('ec2', region_name=region)
    response = client.describe_instances()
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name']!='terminated':
                if 'Tags' in instance:
                    if len(instance['Tags']) > 0:
                        tag_value = instance['Tags'][0]['Value']
                        if tag_value.startswith('ar-'):
                            instance['region'] = region
                            instances.append(instance)

    return instances


def get_instances():
    regions = [
        "us-east-1", 
        "us-east-2", 
        "us-west-1", 
        "us-west-2", 
        "ca-central-1", 
        "eu-west-1", 
        "eu-west-2", 
        "eu-central-1", 
        "ap-southeast-1", 
        "ap-southeast-2", 
        "ap-south-1", 
        "ap-northeast-1", 
        "ap-northeast-2", 
        "sa-east-1"
    ]
    
    instances = []
    for region in regions:
        instances.extend(get_all_instances_in_region(region))

    return instances


def change_instance_state(instances):
    for instance in instances:
        stop_time_reached = instance['LaunchTime'] < datetime.now(timezone.utc) - timedelta(days=DAYS_TO_STOP)
        if instance['State']['Name']=='running' and stop_time_reached:
            print("Stop instance " + instance['InstanceId'] + " . Age:" + str(datetime.now(timezone.utc) - instance['LaunchTime'])  + " region: " + instance['region'])

        if instance['StateTransitionReason']:
            terminate_time_reached = datetime.strptime(instance['StateTransitionReason'][16:-5], '%Y-%m-%d %H:%M:%S') < datetime.utcnow() - timedelta(days=DAYS_TO_TERMINATE )
            if instance['State']['Name']=='stopped' and terminate_time_reached:
                print("Terminate instance " + instance['InstanceId'] + " . Age:" + str(datetime.utcnow() - datetime.strptime(instance['StateTransitionReason'][16:-5], '%Y-%m-%d %H:%M:%S')) + " region: " + instance['region'])


def stop_instance(instance):
    client = boto3.client('ec2', region_name=instance["region"])
    response = client.stop_instances(
        InstanceIds=[instance['InstanceId']]
    )


def terminate_instance(instance):
    client = boto3.client('ec2', region_name=instance["region"])
    response = client.terminate_instances(
        InstanceIds=[instance['InstanceId']]
    )


if __name__ == "__main__":
    main(sys.argv[1:])

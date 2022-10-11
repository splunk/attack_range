import os
import sys
import boto3
import time
import requests
import json


from datetime import datetime, timezone, timedelta

DAYS_TO_STOP = 7
DAYS_TO_TERMINATE = 30
SLEEP_TIMER_BETWEEN_OPERATIONS = 30

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

    #regions = ["eu-west-2"]
    
    instances = []
    for region in regions:
        instances.extend(get_all_instances_in_region(region))

    return instances


def change_instance_state(instances):
    for instance in instances:
        stop_time_reached = instance['LaunchTime'] < datetime.now(timezone.utc) - timedelta(days=DAYS_TO_STOP)
        instance_name = instance['Tags'][0]['Value']
        if instance['State']['Name']=='running' and stop_time_reached:
            msg = "Stop instance " + instance_name + " . Age:" + str(datetime.now(timezone.utc) - instance['LaunchTime'])  + " region: " + instance['region']
            print(msg)
            send_slack_message(msg)
            stop_instance(instance)

        if instance['StateTransitionReason']:
            terminate_time_reached = datetime.strptime(instance['StateTransitionReason'][16:-5], '%Y-%m-%d %H:%M:%S') < datetime.utcnow() - timedelta(days=DAYS_TO_TERMINATE )
            if instance['State']['Name']=='stopped' and terminate_time_reached:
                msg = "Terminate instance " + instance_name + " . Age:" + str(datetime.utcnow() - datetime.strptime(instance['StateTransitionReason'][16:-5], '%Y-%m-%d %H:%M:%S')) + " region: " + instance['region']
                print(msg)
                send_slack_message(msg)
                terminate_instance(instance)


def stop_instance(instance):
    client = boto3.client('ec2', region_name=instance["region"])
    response = client.stop_instances(
        InstanceIds=[instance['InstanceId']]
    )


def terminate_instance(instance):
    client = boto3.client('ec2', region_name=instance["region"])
    try:
        response = client.terminate_instances(
            InstanceIds=[instance['InstanceId']]
        )
    except Exception as e:
        print(e)

    for i in range(10):
        response = client.describe_instances(
            InstanceIds=[instance["InstanceId"]]
        )
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == "terminated":
            break
        time.sleep(30)

    # delete security group
    try:
        response = client.delete_security_group(
            GroupId=instance["SecurityGroups"][0]["GroupId"]
        )
    except Exception as e:
        print(e)

    time.sleep(SLEEP_TIMER_BETWEEN_OPERATIONS)

    # delete subnet
    try:
        response = client.delete_subnet(
            SubnetId=instance["SubnetId"]
        )
    except Exception as e:
        print(e)

    # delete route tables
    response = client.describe_route_tables(
            Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    instance["VpcId"],
                ]
            },
        ]
    )

    time.sleep(SLEEP_TIMER_BETWEEN_OPERATIONS)

    if response['RouteTables']:
        try:
            response = client.delete_route_table(
                RouteTableId=response['RouteTables'][0]['RouteTableId']
            )
        except Exception as e:
            print(e)    

    time.sleep(SLEEP_TIMER_BETWEEN_OPERATIONS)

    # delete internet gateways
    response = client.describe_internet_gateways(
            Filters=[
            {
                'Name': 'attachment.vpc-id',
                'Values': [
                    instance["VpcId"],
                ]
            },
        ]
    )

    time.sleep(SLEEP_TIMER_BETWEEN_OPERATIONS)

    if response['InternetGateways']:
        igw_id = response['InternetGateways'][0]['InternetGatewayId']
        try:
            response = client.detach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=instance["VpcId"]
            )
        except Exception as e:
            print(e)          

        time.sleep(SLEEP_TIMER_BETWEEN_OPERATIONS)

        try:
            response = client.delete_internet_gateway(
                InternetGatewayId=igw_id,
            )
        except Exception as e:
            print(e)  

    time.sleep(SLEEP_TIMER_BETWEEN_OPERATIONS)

    # delete vpc (can fail)
    try:
        response = client.delete_vpc(
            VpcId=instance["VpcId"]
        )
    except Exception as e:
        print(e)


def send_slack_message(msg):
    if os.environ["SLACK_WEBHOOK"]:
        state = requests.post(os.environ["SLACK_WEBHOOK"], json.dumps({"text": msg}))
    else:
        print("ERROR: couldn't find environment variable SLACK_WEBHOOK")


if __name__ == "__main__":
    main(sys.argv[1:])

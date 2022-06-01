
import boto3


def get_all_instances(key_name, region):
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
                    tag_value = instance['Tags'][0]['Value']
                    if tag_value.startswith('ar-'):
                        if key_name in tag_value:
                            instances.append(instance)

    return instances


def get_instance_by_name(ec2_name, key_name, region):
    instances = get_all_instances(key_name, region)
    for instance in instances:
        str = instance['Tags'][0]['Value']
        if str == ec2_name:
            return instance


def get_single_instance_public_ip(ec2_name, key_name, region):
    instance = get_instance_by_name(ec2_name, key_name, region)
    return instance['NetworkInterfaces'][0]['Association']['PublicIp']
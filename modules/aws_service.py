
import boto3


def get_all_instances(key_name, ar_name, region):
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
                        if (key_name in tag_value) and (key_name in tag_value):
                            instances.append(instance)

    return instances


def get_instance_by_name(ec2_name, key_name, ar_name, region):
    instances = get_all_instances(key_name, ar_name, region)
    for instance in instances:
        str = instance['Tags'][0]['Value']
        if str == ec2_name:
            return instance


def get_single_instance_public_ip(ec2_name, key_name, ar_name, region):
    instance = get_instance_by_name(ec2_name, key_name, ar_name, region)
    return instance['NetworkInterfaces'][0]['Association']['PublicIp']


def change_ec2_state(instances, new_state, log, region):
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
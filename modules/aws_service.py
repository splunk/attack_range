
import boto3


def check_region(config_region):
    session = boto3.session.Session()
    aws_cli_region = session.region_name
    return (aws_cli_region == config_region)


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


def query_amis(ami_names, region):
    client = boto3.client('ec2', region_name=region)
    images = client.describe_images(Owners=['self'])
    
    not_found_images = []

    for ami_name in ami_names:
        ami_found = False
        for ami in images["Images"]:
            if ami_name == ami["Name"]:
                ami_found = True

        if not ami_found:
            not_found_images.append(ami_name)   

    return not_found_images


def get_image_id(ami_name, region):
    client = boto3.client('ec2', region_name=region)
    images = client.describe_images(Owners=['self'])

    for ami in images["Images"]:
        if ami_name == ami["Name"]:
            return ami["ImageId"]

def query_amis_all_regions(ami_names, not_found_images):
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
        "sa-east-1", 
        "cn-north-1"
    ]

    ami_region = {}

    for region in regions:
        try:
            not_found_images_region = query_amis(ami_names, region)
            diff_images = list(set(not_found_images) - set(not_found_images_region))
            if diff_images:
                for image in diff_images:
                    if region in ami_region:
                        ami_region[image].append({"region": region, "image_id": get_image_id(image, region)})
                    else:
                        ami_region[image] = [{"region": region, "image_id": get_image_id(image, region)}]

        except:
            pass

    return ami_region


def copy_image(ami_name, ami_image_id, source_region, dest_region):
    session = boto3.client('ec2',region_name=dest_region)

    response = session.copy_image(
        Name=ami_name,
        Description='Copied this AMI from region ' + source_region,
        SourceImageId=ami_image_id,
        SourceRegion=source_region
    )

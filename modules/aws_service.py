
import boto3
import sys
import os
import json
import time


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
                        if (key_name in tag_value) and (ar_name in tag_value):
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


def ami_available(ami_name, region):
    client = boto3.client('ec2', region_name=region)
    try:
        images = client.describe_images(Owners=['self'])
    except:
        return False

    for image in images["Images"]:
        if 'Name' in image:
            if ami_name == image["Name"]:
                if image["State"] == "available":
                    return True

    return False


def ami_available_other_region(ami_name):
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

    for region in regions:
        if ami_available(ami_name, region):
            return {"region": region, "image_id": get_image_id(ami_name, region)}

    return {}



def get_image_id(ami_name, region):
    client = boto3.client('ec2', region_name=region)
    images = client.describe_images(Owners=['self'])

    for ami in images["Images"]:
        if ami_name == ami["Name"]:
            return ami["ImageId"]


def copy_image(ami_name, ami_image_id, source_region, dest_region):
    session = boto3.client('ec2',region_name=dest_region)

    response = session.copy_image(
        Name=ami_name,
        Description='Copied this AMI from region ' + source_region,
        SourceImageId=ami_image_id,
        SourceRegion=source_region
    )

    for x in range(0, 10):
        if ami_available(ami_name, dest_region):
            break
        print("Image not yet available. " + str(10-x) + " tries left.")
        time.sleep(60)

    if not ami_available(ami_name, dest_region):
        print("Error: Copying of AMI took longer as expected.")
        sys.exit(1)


def check_s3_bucket(bucket_name):
    client = boto3.client('s3')
    some_binary_data = b'Here we have some data'

    try:
        client.put_object(Body=some_binary_data, Bucket=bucket_name, Key='test.txt')
        client.delete_object(Bucket=bucket_name, Key='test.txt')
    except Exception as e:
        return False

    return True


def create_s3_bucket(bucket_name, region, logger):
    client = boto3.client("s3", region_name=region)
    location = {'LocationConstraint': region}
    
    try:
        response = client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except Exception as e:
        logger.error("Couldn't create S3 bucket with name " + bucket_name)
        logger.error(e)
        sys.exit(1)

    logger.info("Created S3 bucket with name " + bucket_name)


def create_dynamoo_db(name, region, logger):
    client = boto3.client('dynamodb', region_name=region)
    try:
        response = client.create_table(
            TableName=name,
            KeySchema=[
                {
                    'AttributeName': 'LockID',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'LockID',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
    except client.exceptions.ResourceInUseException:
        logger.info("DynamoDB table already exists with name " + name)
        return
    except Exception as e:
        logger.error("Couldn't create DynamoDB table with name " + name)
        logger.error(e)
        sys.exit(1)

    logger.info("Created DynamoDB table with name " + name)


def delete_s3_bucket(bucket_name, region, logger):
    s3 = boto3.resource('s3', region_name=region)
    try:
        bucket = s3.Bucket(bucket_name)
        bucket.objects.all().delete()
        bucket.delete()
    except Exception as e:
        logger.error("Couldn't delete S3 bucket with name " + bucket_name)
        logger.error(e)
        return
    logger.info("Deleted S3 bucket with name " + bucket_name)


def delete_dynamo_db(name, region, logger):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    try:
        table = dynamodb.Table(name)
        table.delete()
    except Exception as e:
        logger.error("Couldn't delete DynamoDB table with name " + name)
        logger.error(e)
        return
    logger.info("Deleted DynamoDB table with name " + name)


def check_secret_exists(name):
    client = boto3.client('secretsmanager')
    response = client.list_secrets()
    for secret in response['SecretList']:
        if secret['Name'] == str(name + '-key'):
            return True

    return False


def create_secret(name, value, config, logger):
    client = boto3.client('secretsmanager')
    key_name = name + '-key'
    config_name = name + '-config'
    try:
        response = client.create_secret(
            Name=key_name,
            SecretString=value
        )
        response = client.create_secret(
            Name=config_name,
            SecretString=json.dumps(config)
        )
    except Exception as e:
        logger.error("Couldn't create secret with name " + name)
        logger.error(e)
        sys.exit(1)

    logger.info("Created secret with name " + name)


def get_secret_key(name, logger):
    client = boto3.client('secretsmanager')

    response = client.get_secret_value(
        SecretId=name + '-key'
    )
    ssh_key_name = name + ".key"
    with open(ssh_key_name, "w") as ssh_key:
        ssh_key.write(response['SecretString'])
    os.chmod(ssh_key_name, 0o600)


def get_secret_config(name, logger):
    client = boto3.client('secretsmanager')
    
    response = client.get_secret_value(
        SecretId=name + '-config'
    )

    return json.loads(response['SecretString'])


def delete_secret(name, logger):
    client = boto3.client('secretsmanager')

    try:
        response = client.delete_secret(
            SecretId=name + '-key',
            ForceDeleteWithoutRecovery=True
        )
        response = client.delete_secret(
            SecretId=name + '-config',
            ForceDeleteWithoutRecovery=True
        )
    except Exception as e:
        logger.error("Couldn't delete secret with name " + name)
        return

    logger.info("Deleted secret with name " + name)


def create_key_pair(name, region, logger):
    aws_session = boto3.Session()
    client = aws_session.client('ec2', region_name=region)

    response = client.create_key_pair(KeyName=name)
    ssh_key_name = name + ".key"
    with open(ssh_key_name, "w") as ssh_key:
        ssh_key.write(response['KeyMaterial'])
    os.chmod(ssh_key_name, 0o600)
    
    logger.info("Created key pair with name " + name)

    return response['KeyMaterial']


def delete_key_pair(name, region, logger):
    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.delete_key_pair(KeyName=name)

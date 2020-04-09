import sys
import re
import boto3
import mysql.connector


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
            if instance['State']['Name']!='terminated':
                str = instance['Tags'][0]['Value']
                if str.startswith('attack-range'):
                    instances.append(instance)

    return instances


def check_ec2_instance_state(ec2_name, state, config):
    instance = get_instance_by_name(ec2_name, config)

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


def deregister_images(images, config, log):
    client = boto3.client('ec2')

    for image in images:
        response = client.describe_images(
            Filters=[
                {
                    'Name': 'name',
                    'Values': [
                        str("packer-" + image + "-" + config['key_name']),
                    ]
                }
            ]
        )
        if len(response['Images']):
            image_obj = response['Images'][0]
            client.deregister_image(ImageId=image_obj['ImageId'])
            log.info('Successfully deregistered AMI ' +  image_obj['Name'] +  ' with AMI ID ' + image_obj['ImageId'] + ' .')
        else:
            log.info('Didn\'t find AMI: ' +  str("packer-" + image + "-" + config['key_name']) + ' .')


## Database operations ##

def provision_db(config, log):
    client = boto3.client('rds')
    responses = client.describe_db_instances(
        DBInstanceIdentifier=str('db-' + config["key_name"])
    )

    #print(responses["DBInstances"][0]["Endpoint"])

    # Connect to server
    cnx = mysql.connector.connect(
        host=responses["DBInstances"][0]["Endpoint"]["Address"],
        port=3306,
        user=config["db_user"],
        password=config["db_password"],
        database="notedb")


    query_create_table_users = ("create table users (id INT NOT NULL AUTO_INCREMENT, first_name VARCHAR(30) NOT NULL, last_name VARCHAR(30) NOT NULL, password VARCHAR(64) NOT NULL, PRIMARY KEY (id))")
    query_create_table_notes = ("create table notes (id INT NOT NULL AUTO_INCREMENT, title VARCHAR(64) NOT NULL, value TEXT NOT NULL, is_public VARCHAR(30), user_id INT NOT NULL, PRIMARY KEY (id), FOREIGN KEY (user_id) REFERENCES users(id))")
    query_insert_into_users = ("insert into users (first_name, last_name, password) VALUES (%s, %s, %s)")
    query_insert_into_notes = ("insert into notes (title, value, is_public, user_id) VALUES (%s,%s,%s,%s)")

    # Get a cursor
    cur = cnx.cursor()

    # Execute a query
    cur.execute(query_create_table_users)
    cur.execute(query_create_table_notes)


    cur.execute(query_insert_into_users,('Luke', 'Skywalker', 'password123!'))
    file = open("serverless_application/data/sample_data_Luke_public.txt")
    for line in file:
        fields = line.split(";")
        title = fields[0]
        value = fields[1]
        cur.execute(query_insert_into_notes,(title, value, 'true', '1'))
    file.close()

    file = open("serverless_application/data/sample_data_Luke_private.txt")
    for line in file:
        fields = line.split(";")
        title = fields[0]
        value = fields[1]
        cur.execute(query_insert_into_notes,(title, value, 'false', '1'))
    file.close()

    cur.execute(query_insert_into_users,('Dave', 'Fischer', 'ChuckNorris123'))
    file = open("serverless_application/data/sample_data_dave_public.txt")
    for line in file:
        fields = line.split(";")
        title = fields[0]
        value = fields[1]
        cur.execute(query_insert_into_notes,(title, value, 'true', '2'))
    file.close()

    file = open("serverless_application/data/sample_data_dave_private.txt")
    for line in file:
        fields = line.split(";")
        title = fields[0]
        value = fields[1]
        cur.execute(query_insert_into_notes,(title, value, 'false', '2'))
    file.close()

    cur.execute("select n.title, n.is_public, u.first_name, u.last_name FROM notes n INNER JOIN users u ON n.user_id = u.id")

    # Fetch one result
    row = cur.fetchall()
    for x in row:
        print(x)

    # Close connection
    cnx.close()

    #create table users (id INT NOT NULL, first_name VARCHAR(30) NOT NULL, last_name VARCHAR(30) NOT NULL, password VARCHAR(64) NOT NULL, PRIMARY KEY (id));
    #create table notes (id INT NOT NULL, title VARCHAR(64) NOT NULL, value TEXT NOT NULL, is_public BOOLEAN, user_id INT NOT NULL, PRIMARY KEY (id), FOREIGN KEY (user_id) REFERENCES users(id));
    #insert into users (first_name, last_name, password) VALUES ('Luke', 'Skywalker', 'password123!');
    #insert into notes (title, value, is_public, user_id) VALUES ('MySQL note','The best way to start investigating this error is by getting more information about it from LATEST FOREIGN KEY ERROR section of SHOW ENGINE INNODB STATUS',true,0);
    # inner join: select n.title, n.is_public, u.first_name, u.last_name FROM notes n INNER JOIN users u ON n.user_id = u.id;

import os
import ansible_runner
import subprocess
import sys
import signal
import yaml
import json

from python_terraform import Terraform, IsNotFlagged
from modules import aws_service, splunk_sdk
from tabulate import tabulate
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController
from modules.purplesharp_simulation_controller import PurplesharpSimulationController


class AwsController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)
        statefile = self.config['general']['attack_range_name'] + ".terraform.tfstate"
        self.config['general']["statepath"] = os.path.join(os.path.dirname(__file__), '../terraform/aws/state', statefile)

        if not aws_service.check_region(self.config['aws']['region']):
            self.logger.error("AWS cli region and region in config file are not the same.")
            sys.exit(1)

        backend_path_tmp = os.path.join(os.path.dirname(__file__), '../terraform/aws/backend.tf.tmp')
        backend_path = os.path.join(os.path.dirname(__file__), '../terraform/aws/backend.tf')

        if self.config["aws"]["use_remote_state"] == "1":
            with open(backend_path_tmp, 'r') as file :
                filedata = file.read()
            filedata = filedata.replace('[region]', self.config['aws']['region'])
            filedata = filedata.replace('[bucket]', self.config['aws']['tf_remote_state_s3_bucket'])
            filedata = filedata.replace('[dynamodb_table]', self.config['aws']['tf_remote_state_dynamo_db_table'])
            with open(backend_path, 'w+') as file:
                file.write(filedata)

        else:
            if os.path.isfile(backend_path):
                os.remove(backend_path)

        working_dir = os.path.join(os.path.dirname(__file__), '../terraform/aws')
        self.terraform = Terraform(working_dir=working_dir,variables=config, parallelism=15, state= self.config['general']["statepath"])

        #if self.config['general']['use_prebuilt_images_with_packer'] == "0":
        for i in range(len(self.config['windows_servers'])):
            image_name = self.config['windows_servers'][i]['windows_image']
            if image_name.startswith("windows-2016"):
                self.config['windows_servers'][i]['windows_ami'] = "Windows_Server-2016-English-Full-Base-*"
            elif image_name.startswith("windows-2019"):
                self.config['windows_servers'][i]['windows_ami'] = "Windows_Server-2019-English-Full-Base-*"
            else:
                self.logger.error("Image " + image_name + " not supported.")
                sys.exit(1)    
    

    def build(self) -> None:
        self.logger.info("[action] > build\n")

        if self.config['general']['use_prebuilt_images_with_packer'] == "1":
            images = []
            if self.config['splunk_server']['byo_splunk'] == "0":
                images.append(self.config['splunk_server']['splunk_image'])
            for windows_server in self.config['windows_servers']:
                images.append(windows_server['windows_image'])
            for linux_server in self.config['linux_servers']:
                images.append(linux_server['linux_image'])
            if self.config["nginx_server"]["nginx_server"] == "1":
                images.append(self.config["nginx_server"]["nginx_image"])
            if self.config["zeek_server"]["zeek_server"] == "1":
                images.append(self.config["zeek_server"]["zeek_image"])        
            if self.config["phantom_server"]["phantom_server"] == "1":
                images.append(self.config["phantom_server"]["phantom_image"])    

            self.logger.info("Check if images are available in region " + self.config['aws']['region'])

            for image in images:
                if not aws_service.ami_available(image, self.config['aws']['region']):
                    self.logger.info("Image " + image + " is not available in region " + self.config['aws']['region'])
                    self.logger.info("Checking if image " + image + " is available in other regions.")
                    result = aws_service.ami_available_other_region(image)
                    if result:
                        self.logger.info("Found image " + image + " in region " + result['region'] + ". Copy it to region " + self.config['aws']['region'])
                        aws_service.copy_image(
                            image, 
                            result['image_id'], 
                            result['region'],
                            self.config['aws']['region']
                        )
                    else:
                        self.logger.info("Image " + image + " need to be built with packer.")
                        self.packer(image)  
                else:
                    self.logger.info("Image " + image + " is available in region " + self.config['aws']['region'])                 
     

        cwd = os.getcwd()
        os.system('cd ' + os.path.join(os.path.dirname(__file__), '../terraform/aws') + '&& terraform init -migrate-state')
        os.system('cd ' + cwd)

        return_code, stdout, stderr = self.terraform.apply(
            capture_output='yes', 
            skip_plan=True, 
            no_color=IsNotFlagged
        )

        if not return_code:
            self.logger.info("attack_range has been built using terraform successfully")

        self.show()


    def destroy(self) -> None:
        self.logger.info("[action] > destroy\n")

        cwd = os.getcwd()
        os.system('cd ' + os.path.join(os.path.dirname(__file__), '../terraform/aws') + '&& terraform init ')
        os.system('cd ' + cwd)

        return_code, stdout, stderr = self.terraform.destroy(
            capture_output='yes', 
            no_color=IsNotFlagged, 
            force=IsNotFlagged, 
            auto_approve=True
        )
            
        self.logger.info("attack_range has been destroy using terraform successfully")


    def packer(self, image_name) -> None:
        self.logger.info("Create golden image for " + image_name + ". This can take up to 30 minutes.\n")
        only_cmd_arg = ""
        path_packer_file = ""

        self.config['general']['use_prebuilt_images_with_packer'] = "0"
        
        if image_name.startswith("splunk"):
            only_cmd_arg = "amazon-ebs.splunk-ubuntu-18-04"
            path_packer_file = "packer/splunk_server/splunk_aws.pkr.hcl"
            command = ["packer", "build", "-force", 
                "-var", "general=" + json.dumps(self.config["general"]), 
                "-var", "aws=" + json.dumps(self.config["aws"]), 
                "-var", "splunk_server=" + json.dumps(self.config["splunk_server"]), 
                "-only=" + only_cmd_arg, path_packer_file]
        
        elif image_name.startswith("windows"):
            only_cmd_arg = "amazon-ebs.windows"
            path_packer_file = "packer/windows_server/windows_aws.pkr.hcl"  
            
            if image_name.startswith("windows-2016"):
                images = {
                    "aws_image": "Windows_Server-2016-English-Full-Base-*",
                    "azure_publisher": "MicrosoftWindowsServer",
                    "azure_offer": "WindowsServer",
                    "azure_sku": "2016-Datacenter",
                    "name": "windows-2016"
                }            
            elif image_name.startswith("windows-2019"):
                images = {
                    "aws_image": "Windows_Server-2019-English-Full-Base-*",
                    "azure_publisher": "MicrosoftWindowsServer",
                    "azure_offer": "WindowsServer",
                    "azure_sku": "2019-Datacenter",
                    "name": "windows-2019"
                }
            else:
                self.logger.error("Image not supported.")
                sys.exit(1)

            command = ["packer", "build", "-force", 
                "-var", "general=" + json.dumps(self.config["general"]), 
                "-var", "aws=" + json.dumps(self.config["aws"]), 
                "-var", "splunk_server=" + json.dumps(self.config["splunk_server"]),  
                "-var", "images=" + json.dumps(images),  
                "-only=" + only_cmd_arg, path_packer_file]

        elif image_name.startswith("linux"):
            only_cmd_arg = "amazon-ebs.ubuntu-18-04"
            path_packer_file = "packer/linux_server/linux_aws.pkr.hcl"
            command = ["packer", "build", "-force", 
                "-var", "general=" + json.dumps(self.config["general"]), 
                "-var", "aws=" + json.dumps(self.config["aws"]), 
                "-var", "splunk_server=" + json.dumps(self.config["splunk_server"]), 
                "-only=" + only_cmd_arg, path_packer_file]
        
        elif image_name.startswith("phantom"):
            only_cmd_arg = "amazon-ebs.phantom"
            path_packer_file = "packer/phantom_server/phantom_aws.pkr.hcl"
            command = ["packer", "build", "-force", 
                "-var", "general=" + json.dumps(self.config["general"]), 
                "-var", "aws=" + json.dumps(self.config["aws"]), 
                "-var", "splunk_server=" + json.dumps(self.config["splunk_server"]), 
                "-var", "phantom_server=" + json.dumps(self.config["phantom_server"]), 
                "-only=" + only_cmd_arg, path_packer_file]

        elif image_name.startswith("zeek"):
            only_cmd_arg = "amazon-ebs.ubuntu-18-04"
            path_packer_file = "packer/zeek_server/zeek_aws.pkr.hcl"
            command = ["packer", "build", "-force", 
                "-var", "general=" + json.dumps(self.config["general"]), 
                "-var", "aws=" + json.dumps(self.config["aws"]), 
                "-var", "splunk_server=" + json.dumps(self.config["splunk_server"]), 
                "-only=" + only_cmd_arg, path_packer_file]
                
        elif image_name.startswith("nginx"):
            only_cmd_arg = "amazon-ebs.nginx-web-proxy"
            path_packer_file = "packer/nginx_server/nginx_aws.pkr.hcl"
            command = ["packer", "build", "-force", 
                "-var", "general=" + json.dumps(self.config["general"]), 
                "-var", "aws=" + json.dumps(self.config["aws"]), 
                "-var", "splunk_server=" + json.dumps(self.config["splunk_server"]), 
                "-only=" + only_cmd_arg, path_packer_file]

        if only_cmd_arg == "":
            self.logger.error("Image not supported.")
            sys.exit(1)

        # disable packer color clears up output 
        envvars = dict(os.environ)
        envvars["PACKER_NO_COLOR"] = "1"

        try:
            process = subprocess.Popen(command, env=envvars, shell=False, universal_newlines=True, stdout=subprocess.PIPE)
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()

    def stop(self) -> None:
        instances = aws_service.get_all_instances(self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region'])
        aws_service.change_ec2_state(instances, 'stopped', self.logger, self.config['aws']['region'])

    def resume(self) -> None:
        instances = aws_service.get_all_instances(self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region'])
        aws_service.change_ec2_state(instances, 'running', self.logger, self.config['aws']['region'])

    def simulate(self, engine, target, technique, playbook) -> None:
        self.logger.info("[action] > simulate\n")
        if engine == "ART":
            simulation_controller = ArtSimulationController(self.config)
            simulation_controller.simulate(target, technique)
        if engine == "PurpleSharp":
            simulation_controller = PurplesharpSimulationController(self.config)
            simulation_controller.simulate(target, technique, playbook)
        

    def show(self) -> None:
        self.logger.info("[action] > show\n")
        instances = aws_service.get_all_instances(self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region'])
        response = []
        messages = []
        instances_running = False
        splunk_ip = ""
        for instance in instances:
            if instance['State']['Name'] == 'running':
                instances_running = True
                response.append([instance['Tags'][0]['Value'], instance['State']['Name'],
                                    instance['NetworkInterfaces'][0]['Association']['PublicIp']])
                instance_name = instance['Tags'][0]['Value']
                if instance_name.startswith("ar-splunk"):
                    splunk_ip = instance['NetworkInterfaces'][0]['Association']['PublicIp']
                    messages.append("\nAccess Guacamole via:\n\tWeb > http://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8080/guacamole" + "\n\tusername: Admin \n\tpassword: " + self.config['general']['attack_range_password'])
                    if self.config["splunk_server"]["install_es"] == "1":
                        messages.append("\nAccess Splunk via:\n\tWeb > https://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8000\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                    else:
                        messages.append("\nAccess Splunk via:\n\tWeb > http://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8000\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-phantom"):
                    if "splunk_soar-unpriv-6" in self.config["phantom_server"]["phantom_app"]:
                        messages.append("\nAccess Phantom via:\n\tWeb > https://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8443" + "\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " centos@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: soar_local_admin \n\tpassword: " + self.config['general']['attack_range_password'])
                    else:
                        messages.append("\nAccess Phantom via:\n\tWeb > https://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8443" + "\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " centos@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-win"):
                    messages.append("\nAccess Windows via:\n\tRDP > rdp://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":3389\n\tusername: Administrator \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-linux"):
                    messages.append("\nAccess Linux via:\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: ubuntu \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-kali"):
                    messages.append("\nAccess Kali via:\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " kali@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: kali \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-nginx"):
                    messages.append("\nAccess Nginx Web Proxy via:\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: kali \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-zeek"):
                    messages.append("\nAccess Zeek via:\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: ubuntu \n\tpassword: " + self.config['general']['attack_range_password'])                
            else:
                response.append([instance['Tags'][0]['Value'],
                                    instance['State']['Name']])

        if self.config['simulation']['prelude'] == "1":
            prelude_token = self.get_prelude_token('/var/tmp/.prelude_session_token')
            messages.append("\nAccess Prelude Operator UI via:\n\tredirector FQDN > " + splunk_ip + "\n\tToken: " + prelude_token + "\n\tSee guide details: https://github.com/splunk/attack_range/wiki/Prelude-Operator")

        print()
        print('Status Virtual Machines\n')
        if len(response) > 0:

            if instances_running:
                print(tabulate(response, headers=[
                      'Name', 'Status', 'IP Address']))
                for msg in messages:
                    print(msg)
            else:
                print(tabulate(response, headers=['Name', 'Status']))

            print()
        else:
            print("ERROR: Can't find configured Attack Range Instances")

    def dump(self, dump_name, search, earliest, latest) -> None:
        self.logger.info("Dump log data")
        dump_search = "search " + search + " earliest=-" + earliest + " latest=" + latest + " | sort 0 _time"
        self.logger.info("Dumping Splunk Search: " + dump_search)
        out = open(os.path.join(os.path.dirname(__file__), "../" + dump_name), 'wb')

        splunk_instance = "ar-splunk-" + self.config['general']['key_name'] + '-' + self.config['general']['attack_range_name']
        splunk_sdk.export_search(aws_service.get_single_instance_public_ip(splunk_instance, self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region']),
                                    s=dump_search,
                                    password=self.config['general']['attack_range_password'],
                                    out=out)
        out.close()
        self.logger.info("[Completed]")

    def replay(self, file_name, index, sourcetype, source) -> None:
        ansible_vars = {}
        ansible_vars['file_name'] = file_name
        ansible_vars['ansible_user'] = 'ubuntu'
        ansible_vars['ansible_ssh_private_key_file'] = self.config['aws']['private_key_path']
        ansible_vars['attack_range_password'] = self.config['general']['attack_range_password']
        ansible_vars['ansible_port'] = 22
        ansible_vars['sourcetype'] = sourcetype
        ansible_vars['source'] = source
        ansible_vars['index'] = index

        splunk_instance = "ar-splunk-" + self.config['general']['key_name'] + '-' + self.config['general']['attack_range_name']
        splunk_ip = aws_service.get_single_instance_public_ip(splunk_instance, self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region'])
        cmdline = "-i %s, -u %s" % (splunk_ip, ansible_vars['ansible_user'])
        runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                    cmdline=cmdline,
                                    roles_path=os.path.join(os.path.dirname(__file__), 'ansible/roles'),
                                    playbook=os.path.join(os.path.dirname(__file__), 'ansible/data_replay.yml'),
                                    extravars=ansible_vars)


    def get_prelude_token(self, token_path):
        token = ''
        try:
            prelude_token_file = open(token_path,'r')
            token = prelude_token_file.read()
        except Exception as e:
            self.logger.error("was not able to read prelude token from {}".format(token_path))
        return token


    def create_remote_backend(self, backend_name) -> None:
        if not aws_service.check_s3_bucket(backend_name):
            self.logger.info("Can not access remote S3 bucket with name " + backend_name)
            self.logger.info("Try to create a S3 for remote backend.")
            aws_service.create_s3_bucket(backend_name, self.config['aws']['region'], self.logger)

        # create DynamoDB
        aws_service.create_dynamoo_db(backend_name, self.config['aws']['region'], self.logger)

        self.config['aws']['private_key_path'] = str(Path(backend_name + '.key').resolve())
        self.config['general']['key_name'] = backend_name

        # privat key in secrets manager
        if not aws_service.check_secret_exists(backend_name):
            key_material = aws_service.create_key_pair(backend_name, self.config['aws']['region'], self.logger)
            aws_service.create_secret(backend_name, key_material, self.config, self.logger)

        with open(os.path.join(os.path.dirname(__file__), '../attack_range.yml'), 'w') as outfile:
            yaml.dump(self.config, outfile, default_flow_style=False, sort_keys=False)

        # write versions.tf
        j2_env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '../terraform/aws')), 
            trim_blocks=True)
        template = j2_env.get_template('versions.tf.j2')
        output = template.render(backend_name=backend_name, region=self.config['aws']['region'])
        with open('terraform/aws/versions.tf', 'w') as f:
            output = output.encode('ascii', 'ignore').decode('ascii')
            f.write(output)


    def delete_remote_backend(self, backend_name) -> None:
        aws_service.delete_s3_bucket(backend_name, self.config['aws']['region'], self.logger)
        aws_service.delete_dynamo_db(backend_name, self.config['aws']['region'], self.logger)
        aws_service.delete_secret(backend_name, self.logger)
        aws_service.delete_key_pair(backend_name, self.config['aws']['region'], self.logger)
        try:
            os.remove(os.path.join(os.path.dirname(__file__), '../terraform/aws/versions.tf'))
        except Exception as e:
            self.logger.error(e)
        try:
            os.remove(os.path.join(os.path.dirname(__file__), '../', backend_name + '.key'))
        except Exception as e:
            self.logger.error(e)


    def init_remote_backend(self, backend_name) -> None:
        if not aws_service.check_s3_bucket(backend_name):
            self.logger.error("Can't find S3 bucket with name " + backend_name)
            sys.exit(1)
        if not aws_service.check_secret_exists(backend_name):
            self.logger.error("Secret doesn't exist with name " + backend_name)
            sys.exit(1)

        aws_service.get_secret_key(backend_name, self.logger)
        config = aws_service.get_secret_config(backend_name, self.logger)
        config['aws']['private_key_path'] = str(Path(backend_name + '.key').resolve())
        with open(os.path.join(os.path.dirname(__file__), '../attack_range.yml'), 'w') as outfile:
            yaml.dump(config, outfile, default_flow_style=False, sort_keys=False)

        # write versions.tf
        j2_env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '../terraform/aws')), 
            trim_blocks=True)
        template = j2_env.get_template('versions.tf.j2')
        output = template.render(backend_name=backend_name, region=self.config['aws']['region'])
        with open('terraform/aws/versions.tf', 'w') as f:
            output = output.encode('ascii', 'ignore').decode('ascii')
            f.write(output)

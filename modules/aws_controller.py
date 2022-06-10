import os
import ansible_runner
import subprocess
import sys
import signal

from python_terraform import Terraform, IsNotFlagged
from modules import aws_service, splunk_sdk
from tabulate import tabulate

from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController


class AwsController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)

        if not aws_service.check_region(self.config['aws']['region']):
            self.logger.error("AWS cli region and region in config file are not the same.")
            sys.exit(1)

        working_dir = os.path.join(os.path.dirname(__file__), '../terraform/aws')
        self.terraform = Terraform(working_dir=working_dir,variables=config, parallelism=15)

    def build(self) -> None:
        self.logger.info("[action] > build\n")

        images = []
        images.append(self.config['splunk_server']['image'])
        for windows_server in self.config['windows_servers']:
            images.append(windows_server['image'])
        for linux_server in self.config['linux_servers']:
            images.append(linux_server['image'])
        if self.config["nginx_server"]["nginx_server"] == "1":
            images.append(self.config["nginx_server"]["image"])        

        self.logger.info("Check if images are available in region " + self.config['aws']['region'])
        not_found_images = aws_service.query_amis(images, self.config['aws']['region'])
        
        if not_found_images: 
            self.logger.info("Images " + ", ".join(not_found_images) + " are not available in region " + self.config['aws']['region'])
            self.logger.info("Checking if images " + ", ".join(not_found_images) + " are available in other regions.")
            ami_region = aws_service.query_amis_all_regions(images, not_found_images)
            for ami_name in ami_region.keys():
                self.logger.info("Found image " + ami_name + " in region " + ami_region[ami_name][0]['region'] + ". Copy it to region " + self.config['aws']['region'])
                aws_service.copy_image(
                    ami_name, 
                    ami_region[ami_name][0]['image_id'], 
                    ami_region[ami_name][0]['region'],
                    self.config['aws']['region']
                )
            
            images_to_build = list(set(images) - set(ami_region.keys()))
            for image in images_to_build:
                self.logger.info("Image " + image + " need to be built with packer.")
                self.packer(image) 

        else:
            self.logger.info("Images " + ", ".join(images) + " are available in region " + self.config['aws']['region'])

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
        if image_name.startswith("splunk"):
            only_cmd_arg = "amazon-ebs.splunk-ubuntu-18-04"
            path_packer_file = "packer/splunk_server/splunk-ubuntu.pkr.hcl"
        elif image_name.startswith("linux"):
            only_cmd_arg = "amazon-ebs.ubuntu-18-04"
            path_packer_file = "packer/linux_server/linux-ubuntu-18-04.pkr.hcl"
        elif image_name.startswith("nginx"):
            only_cmd_arg = "amazon-ebs.nginx-web-proxy"
            path_packer_file = "packer/nginx_server/nginx_web_proxy.pkr.hcl"
        elif image_name.startswith("windows-2016"):
            only_cmd_arg = "amazon-ebs.windows"
            path_packer_file = "packer/windows_server/windows_2016.pkr.hcl"                      
        elif image_name.startswith("windows-2019"):
            only_cmd_arg = "amazon-ebs.windows"
            path_packer_file = "packer/windows_server/windows_2019.pkr.hcl"  

        if only_cmd_arg == "":
            self.logger.error("Image not supported.")
            sys.exit(1)

        try:
            process = subprocess.Popen(["packer", "build", "-force", "-only=" + only_cmd_arg, path_packer_file],shell=False,stdout=subprocess.PIPE)
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

    def show(self) -> None:
        self.logger.info("[action] > show\n")
        instances = aws_service.get_all_instances(self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region'])
        response = []
        messages = []
        instances_running = False
        for instance in instances:
            if instance['State']['Name'] == 'running':
                instances_running = True
                response.append([instance['Tags'][0]['Value'], instance['State']['Name'],
                                    instance['NetworkInterfaces'][0]['Association']['PublicIp']])
                instance_name = instance['Tags'][0]['Value']
                if instance_name.startswith("ar-splunk"):
                    if self.config["splunk_server"]["install_es"] == "1":
                        messages.append("\nAccess Splunk via:\n\tWeb > https://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8000\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                    else:
                        messages.append("\nAccess Splunk via:\n\tWeb > http://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8000\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-phantom"):
                    messages.append("\nAccess Phantom via:\n\tWeb > https://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " centos@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-win"):
                    messages.append("\nAccess Windows via:\n\tRDP > rdp://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":3389\n\tusername: Administrator \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-linux"):
                    messages.append("\nAccess Linux via:\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: ubuntu \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-kali"):
                    messages.append("\nAccess Kali via:\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " kali@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: kali \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-nginx"):
                    messages.append("\nAccess Nginx Web Proxy via:\n\tSSH > ssh -i" + self.config['aws']['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: kali \n\tpassword: " + self.config['general']['attack_range_password'])                
            else:
                response.append([instance['Tags'][0]['Value'],
                                    instance['State']['Name']])

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
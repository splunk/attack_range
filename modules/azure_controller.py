import os
import ansible_runner
import subprocess
import sys
import signal

from python_terraform import Terraform, IsNotFlagged
from tabulate import tabulate

from modules import azure_service, splunk_sdk
from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController


class AzureController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)
        working_dir = os.path.join(os.path.dirname(__file__), '../terraform/azure')
        self.terraform = Terraform(working_dir=working_dir,variables=config, parallelism=15)

    def build(self) -> None:
        self.logger.info("[action] > build\n")

        images = []
        images.append(self.config['splunk_server']['image'])
        for windows_server in self.config['windows_servers']:
            images.append(windows_server['image'])
        for linux_server in self.config['linux_servers']:
            images.append(linux_server['image'])       

        for ar_image in images:
            self.logger.info("Check if image " + ar_image + " are available in region " + self.config['azure']['region'])
            if not azure_service.check_image_available(ar_image, self.config['azure']['region']):
                self.logger.info("Image " + ar_image + " is not available in region " + self.config['azure']['region'] + ". Create a golden image with packer.")
                self.packer(ar_image)
            else:
                self.logger.info("Image " + ar_image + " is available in region " + self.config['azure']['region'])

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

    def stop(self) -> None:
        azure_service.change_instance_state(self.config['general']['key_name'], self.config['general']['attack_range_name'], 'stopped', self.logger)

    def resume(self) -> None:
        azure_service.change_instance_state(self.config['general']['key_name'], self.config['general']['attack_range_name'], 'running', self.logger)

    def packer(self, image_name) -> None:
        self.logger.info("Create golden image for " + image_name + ". This can take up to 30 minutes.\n")
        azure_service.create_ressource_group(self.config['azure']['region'])
        only_cmd_arg = ""
        path_packer_file = ""
        if image_name.startswith("splunk"):
            only_cmd_arg = "azure-arm.splunk-ubuntu-18-04"
            path_packer_file = "packer/splunk_server/splunk-ubuntu.pkr.hcl"
        elif image_name.startswith("linux"):
            only_cmd_arg = "azure-arm.ubuntu-18-04"
            path_packer_file = "packer/linux_server/linux-ubuntu-18-04.pkr.hcl"
        elif image_name.startswith("windows-2016"):
            only_cmd_arg = "azure-arm.windows"
            path_packer_file = "packer/windows_server/windows_2016.pkr.hcl"                      
        elif image_name.startswith("windows-2019"):
            only_cmd_arg = "azure-arm.windows"
            path_packer_file = "packer/windows_server/windows_2019.pkr.hcl"  
        elif image_name.startswith("windows-10"):
            only_cmd_arg = "azure-arm.windows"
            path_packer_file = "packer/windows_server/windows_10.pkr.hcl"  
        elif image_name.startswith("windows-11"):
            only_cmd_arg = "azure-arm.windows"
            path_packer_file = "packer/windows_server/windows_10.pkr.hcl"  

        if only_cmd_arg == "":
            self.logger.error("Image not supported.")
            sys.exit(1)

        try:
            process = subprocess.Popen(["packer", "build", "-force", "-var", "location_azure=" + self.config['azure']['region'] , "-only=" + only_cmd_arg, path_packer_file],shell=False,stdout=subprocess.PIPE)
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)

        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()


    def simulate(self, engine, target, technique, playbook) -> None:
        self.logger.info("[action] > simulate\n")
        if engine == "ART":
            simulation_controller = ArtSimulationController(self.config)
            simulation_controller.simulate(target, technique)


    def show(self) -> None:
        self.logger.info("[action] > show\n")
        instances = azure_service.get_all_instances(self.config['general']['key_name'], self.config['general']['attack_range_name'])
        response = []
        messages = []
        instances_running = False
        for instance in instances:
            if instance['vm_obj'].instance_view.statuses[1].display_status == "VM running":
                instances_running = True
                response.append([instance['vm_obj'].name, 
                    instance['vm_obj'].instance_view.statuses[1].display_status, instance['public_ip']])
                instance_name = instance['vm_obj'].name
                if instance_name.startswith("ar-splunk"):
                    if self.config["splunk_server"]["install_es"] == "1":
                        messages.append("\n\nAccess Splunk via:\n\tWeb > https://" + instance['public_ip'] + ":8000\n\tSSH > ssh -i" + self.config['azure']['private_key_path'] + " ubuntu@" + instance['public_ip'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                    else:
                        messages.append("\n\nAccess Splunk via:\n\tWeb > http://" + instance['public_ip'] + ":8000\n\tSSH > ssh -i" + self.config['azure']['private_key_path'] + " ubuntu@" + instance['public_ip'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-phantom"):
                    messages.append("\nAccess Phantom via:\n\tWeb > https://" + instance['public_ip'] + "\n\tSSH > ssh -i" + self.config['azure']['private_key_path'] + " centos@" + instance['public_ip'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-win"):
                    messages.append("\nAccess Windows via:\n\tRDP > rdp://" + instance['public_ip'] + ":3389\n\tusername: AzureAdmin \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-linux"):
                    messages.append("\nAccess Linux via:\n\tSSH > ssh -i" + self.config['azure']['private_key_path'] + " ubuntu@" + instance['public_ip'] + "\n\tusername: ubuntu \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-kali"):
                    messages.append("\nAccess Kali via:\n\tSSH > ssh -i" + self.config['azure']['private_key_path'] + " kali@" + instance['public_ip'] + "\n\tusername: kali \n\tpassword: " + self.config['general']['attack_range_password'])
                elif instance_name.startswith("ar-nginx"):
                    messages.append("\nAccess Nginx Web Proxy via:\n\tSSH > ssh -i" + self.config['azure']['private_key_path'] + " ubuntu@" + instance['public_ip'] + "\n\tusername: kali \n\tpassword: " + self.config['general']['attack_range_password'])           
            else:
                response.append([instance['vm_obj'].name, 
                    instance['vm_obj'].instance_view.statuses[1].display_status])

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
        splunk_sdk.export_search(azure_service.get_instance(splunk_instance, self.config['general']['key_name'], self.config['general']['attack_range_name'])['public_ip'],
                                    s=dump_search,
                                    password=self.config['general']['attack_range_password'],
                                    out=out)
        out.close()
        self.logger.info("[Completed]")


    def replay(self, file_name, index, sourcetype, source) -> None:
        ansible_vars = {}
        ansible_vars['file_name'] = file_name
        ansible_vars['ansible_user'] = 'ubuntu'
        ansible_vars['ansible_ssh_private_key_file'] = self.config['azure']['private_key_path']
        ansible_vars['attack_range_password'] = self.config['general']['attack_range_password']
        ansible_vars['ansible_port'] = 22
        ansible_vars['sourcetype'] = sourcetype
        ansible_vars['source'] = source
        ansible_vars['index'] = index

        splunk_instance = "ar-splunk-" + self.config['general']['key_name'] + '-' + self.config['general']['attack_range_name']
        splunk_ip = azure_service.get_instance(splunk_instance, self.config['general']['key_name'], self.config['general']['attack_range_name'])['public_ip']
        cmdline = "-i %s, -u %s" % (splunk_ip, ansible_vars['ansible_user'])
        runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                    cmdline=cmdline,
                                    roles_path=os.path.join(os.path.dirname(__file__), 'ansible/roles'),
                                    playbook=os.path.join(os.path.dirname(__file__), 'ansible/data_replay.yml'),
                                    extravars=ansible_vars)
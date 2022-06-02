import os

from python_terraform import Terraform, IsNotFlagged
from tabulate import tabulate

from modules import azure_service
from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController


class AzureController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)
        working_dir = os.path.join(os.path.dirname(__file__), '../terraform/azure')
        self.terraform = Terraform(working_dir=working_dir,variables=config, parallelism=15)

    def build(self) -> None:
        self.logger.info("[action] > build\n")
        return_code, stdout, stderr = self.terraform.apply(
            capture_output='yes', 
            skip_plan=True, 
            no_color=IsNotFlagged
        )
        if not return_code:
            self.logger.info("attack_range has been built using terraform successfully")

    def destroy(self) -> None:
        self.logger.info("[action] > destroy\n")
        return_code, stdout, stderr = self.terraform.destroy(
            capture_output='yes', 
            no_color=IsNotFlagged, 
            force=IsNotFlagged, 
            auto_approve=True
        )
        self.logger.info("attack_range has been destroy using terraform successfully")

    def simulate(self, engine, target, technique, playbook) -> None:
        self.logger.info("[action] > simulate\n")
        if engine == "ART":
            simulation_controller = ArtSimulationController(self.config)
            simulation_controller.simulate(target, technique)


    def show(self) -> None:
        self.logger.info("[action] > show\n")
        instances = azure_service.get_all_instances(self.config['general']['key_name'])
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
                    messages.append("\nAccess Windows via:\n\tRDP > rdp://" + instance['public_ip'] + ":3389\n\tusername: Administrator \n\tpassword: " + self.config['general']['attack_range_password'])
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
import os

from python_terraform import Terraform, IsNotFlagged
from modules import aws_service
from tabulate import tabulate

from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController


class AwsController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)
        working_dir = os.path.join(os.path.dirname(__file__), '../terraform/aws')
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
        instances = aws_service.get_all_instances(self.config['general']['key_name'], self.config['aws']['region'])
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
                        messages.append("\n\nAccess Splunk via:\n\tWeb > https://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8000\n\tSSH > ssh -i" + self.config['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                    else:
                        messages.append("\n\nAccess Splunk via:\n\tWeb > http://" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + ":8000\n\tSSH > ssh -i" + self.config['private_key_path'] + " ubuntu@" + instance['NetworkInterfaces'][0]['Association']['PublicIp'] + "\n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                    
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

    # def getIP(self, response, machine_type):
    #     for machine in response:
    #         for x in machine:
    #             if machine_type in x:
    #                 try:
    #                     ip = machine[2]
    #                 except Exception as e:
    #                     self.log.debug("not able to get instance ip")
    #                     ip = ''
    #                 return ip

    # def show_message(self, response):
    #     print_messages = []

    #     # splunk server will always be built
    #     splunk_ip = self.getIP(response, 'splunk')
    #     if self.config['install_es'] == "1":
    #         msg = "\n\nAccess Splunk via:\n\tWeb > https://" + splunk_ip + ":8000\n\tSSH > ssh -i" + self.config['private_key_path'] + " ubuntu@" + splunk_ip + "\n\tusername: admin \n\tpassword: " + self.config['attack_range_password']
    #         print_messages.append(msg)
    #     else:
    #         msg = "\n\nAccess Splunk via:\n\tWeb > http://" + splunk_ip + ":8000\n\tSSH > ssh -i" + self.config['private_key_path'] + " ubuntu@" + splunk_ip + "\n\tusername: admin \n\tpassword: " + self.config['attack_range_password']
    #         print_messages.append(msg)

    #     # windows domain controller
    #     if self.config['windows_domain_controller'] == "1":
    #         win_ip = self.getIP(response, 'win-dc')
    #         msg = "Access Windows Domain Controller via:\n\tRDP > rdp://" + win_ip + ":3389\n\tusername: Administrator \n\tpassword: " + self.config['attack_range_password']
    #         print_messages.append(msg)

    #     # windows domain controller
    #     if self.config['windows_server'] == "1":
    #         win_server = self.getIP(response, 'win-server')
    #         msg = "Access Windows Server via:\n\tRDP > rdp://" + win_server + ":3389\n\tusername: Administrator \n\tpassword: " + self.config['attack_range_password']
    #         print_messages.append(msg)

    #     # kali linux
    #     if self.config['kali_machine'] == "1":
    #         kali_ip = self.getIP(response, 'kali')
    #         msg = "Access Kali via:\n\tSSH > ssh -i" + self.config['private_key_path'] \
    #         + " kali@" + kali_ip + "\n\tusername: kali \n\tpassword: " + self.config['attack_range_password']
    #         print_messages.append(msg)

    #     # osquery linux
    #     if self.config['osquery_machine'] == "1":
    #         osquerylnx_ip = self.getIP(response, 'osquerylnx')
    #         msg = "Access Osquery via:\n\tSSH > ssh -i" + self.config['private_key_path'] \
    #         + " ubuntu@" + osquerylnx_ip + "\n\tusername: kali \n\tpassword: " + self.config['attack_range_password']
    #         print_messages.append(msg)

    #     # phantom linux
    #     if self.config['phantom_server'] == "1":
    #         phantom_ip = self.getIP(response, 'phantom')
    #         msg = "Access Phantom via:\n\tWeb > https://" + phantom_ip + "\n\tSSH > ssh -i" + self.config['private_key_path'] \
    #         + " centos@" + phantom_ip + "\n\tusername: admin \n\tpassword: " + self.config['attack_range_password']
    #         print_messages.append(msg)

    #     # nginx_web_proxy
    #     if self.config['nginx_web_proxy'] == "1":
    #         nginx_web_proxy = self.getIP(response, 'nginx_web_proxy')
    #         msg = "Access Nginx Web Proxy via:\n\tSSH > ssh -i" + self.config['private_key_path'] \
    #         + " ubuntu@" + nginx_web_proxy
    #         print_messages.append(msg)

    #     # nginx_web_proxy
    #     if self.config['sysmon_linux'] == "1":
    #         sysmon_linux_ip = self.getIP(response, 'sysmon_linux')
    #         msg = "Access Sysmon Linux via:\n\tSSH > ssh -i" + self.config['private_key_path'] \
    #         + " ubuntu@" + sysmon_linux_ip
    #         print_messages.append(msg)

    #     return print_messages
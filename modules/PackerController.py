
from modules.IEnvironmentController import IEnvironmentController
import hashlib
import re
from packerpy import PackerExecutable
from python_terraform import *
from jinja2 import Environment, FileSystemLoader
from modules import aws_service, splunk_sdk
from tabulate import tabulate
import ansible_runner


class PackerController(IEnvironmentController):


    def __init__(self, config, log, force):
        super().__init__(config, log)
        self.force = force
        self.p = PackerExecutable("/usr/local/bin/packer")

        custom_dict = self.config.copy()
        rem_list = ['hash_value', 'log_path', 'log_level', 'windows_client', 'windows_client_os', 'windows_client_private_ip', 'windows_client_join_domain', 'art_run_techniques']
        [custom_dict.pop(key) for key in rem_list]
        custom_dict['ip_whitelist'] = [custom_dict['ip_whitelist']]
        custom_dict['use_packer_amis'] = '1'
        custom_dict['splunk_packer_ami'] = "packer-splunk-server-" + self.config['key_name']
        custom_dict['windows_domain_controller_packer_ami'] = "packer-windows-domain-controller-" + self.config['key_name']
        self.terraform = Terraform(working_dir='terraform',variables=custom_dict)


    def write_hash_value(self, hash_value):
        # write new hash value into attack-range.conf
        with open('default/attack_range.conf.default', 'r') as file:
            attack_range_conf = file.read()

        attack_range_conf = re.sub(r'hash_value = .+', 'hash_value = ' + str(hash_value), attack_range_conf, re.M)

        with open('default/attack_range.conf.default', 'w') as file:
            file.write(attack_range_conf)


    def read_and_write_userdata_file(self):
        j2_env = Environment(loader=FileSystemLoader('packer/script'),trim_blocks=True)
        template = j2_env.get_template('userdata.ps1.j2')
        userdata_file = template.render(self.config)
        with open('packer/script/userdata.ps1', 'w') as file:
            file.write(userdata_file)


    def build(self):
        self.log.info("[action] > build\n")
        self.md5_hash = hashlib.md5(open('attack_range.conf','rb').read()).hexdigest()
        if self.md5_hash != self.config['hash_value'] or self.force:
            packer_amis = ['splunk-server']
            #packer_amis = []
            if self.config['windows_domain_controller']=='1':
                self.read_and_write_userdata_file()
                packer_amis.append('windows-domain-controller')
            if self.config['windows_server']=='1':
                self.read_and_write_userdata_file()
                packer_amis.append('windows-server')
            if self.config['kali_machine']=='1':
                packer_amis.append('kali_machine')

            for packer_ami in packer_amis:
                self.log.info("Generate new Packer AMI packer-" + packer_ami + "-" + self.config['key_name'] + ". This can take some time.")
                template = 'packer/' + packer_ami +'/packer.json'
                template_vars = self.config
                template_vars['splunk_indexer_ip'] = self.config['splunk_server_private_ip']
                (ret, out, err) = self.p.build(template,var=template_vars)
                if ret:
                    self.log.error("ERROR: " + str(out))
                    sys.exit(1)
                self.log.info("successfully generated Packer AMI packer-" + packer_ami + "-" + self.config['key_name'])

        # To Do: check for amis using boto3
        self.build_terraform()
        self.write_hash_value(self.md5_hash)


    def build_terraform(self):
        self.log.info("build terraform with packer amis")
        return_code, stdout, stderr = self.terraform.apply(capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        if not return_code:
            self.log.info("attack_range has been built using terraform successfully")
            self.list_machines()


    def destroy(self):
        self.log.info("[action] > destroy\n")
        return_code, stdout, stderr = self.terraform.destroy(capture_output='yes', no_color=IsNotFlagged)
        self.log.info("attack_range has been destroy using terraform successfully")


    def stop(self):
        instances = aws_service.get_all_instances(self.config)
        aws_service.change_ec2_state(instances, 'stopped', self.log)


    def resume(self):
        instances = aws_service.get_all_instances(self.config)
        aws_service.change_ec2_state(instances, 'running', self.log)


    def simulate(self, target, simulation_techniques):
        target_public_ip = aws_service.get_single_instance_public_ip(target, self.config)
        runner = ansible_runner.run(private_data_dir='.attack_range/',
                               cmdline=str('-i ' + target_public_ip + ', '),
                               roles_path="../ansible/roles",
                               playbook='../ansible/playbooks/atomic_red_team.yml',
                               extravars={'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['win_password']},
                               verbosity=0)

        if runner.status == "successful":
            self.log.info("successfully executed technique ID {0} against target: {1}".format(simulation_techniques, target))
        else:
            self.log.error("failed to executed technique ID {0} against target: {1}".format(simulation_techniques, target))
            sys.exit(1)


    def search(self, search_name):
        instance = aws_service.get_instance_by_name("attack-range-splunk-server",self.config)
        if instance['State']['Name'] == 'running':
            splunk_sdk.search(instance['NetworkInterfaces'][0]['Association']['PublicIp'],str(self.config['splunk_admin_password']), search_name, self.log)
        else:
            self.log.error('ERROR: Splunk server is not running.')


    def list_machines(self):
        instances = aws_service.get_all_instances(self.config)
        response = []
        instances_running = False
        for instance in instances:
            if instance['State']['Name'] == 'running':
                instances_running = True
                response.append([instance['Tags'][0]['Value'], instance['State']['Name'], instance['NetworkInterfaces'][0]['Association']['PublicIp']])
            else:
                response.append([instance['Tags'][0]['Value'], instance['State']['Name']])
        print()
        print('Terraform Status\n')
        if len(response) > 0:
            if instances_running:
                print(tabulate(response, headers=['Name','Status', 'IP Address']))
            else:
                print(tabulate(response, headers=['Name','Status']))
        else:
            print("ERROR: Can't find configured EC2 Attack Range Instances in AWS.")
            sys.exit(1)
        print()


    def list_searches(self):
        instance = aws_service.get_instance_by_name("attack-range-splunk-server",self.config)
        if instance['State']['Name'] == 'running':
            response = splunk_sdk.list_searches(instance['NetworkInterfaces'][0]['Association']['PublicIp'],str(self.config['splunk_admin_password']))
            if len(response) > 0:
                objects = []
                for object in response:
                    objects.append([object.name])
                print()
                print('Available savedsearches in Splunk\n')
                print(tabulate(objects, headers=['Name']))
                print()
        else:
            log.error('ERROR: Splunk server is not running.')

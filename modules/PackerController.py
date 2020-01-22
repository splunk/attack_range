
from modules.IEnvironmentController import IEnvironmentController
import hashlib
import re
from packerpy import PackerExecutable
from python_terraform import *


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


    def build(self):
        self.log.info("[action] > build\n")
        self.md5_hash = hashlib.md5(open('attack_range.conf','rb').read()).hexdigest()
        if self.md5_hash != self.config['hash_value'] or self.force:
            #packer_amis = ['splunk-server']
            packer_amis = []
            if self.config['windows_domain_controller']=='1':
                packer_amis.append('windows-domain-controller')
            if self.config['windows_server']=='1':
                packer_amis.append('windows-server')
            if self.config['kali_machine']=='1':
                packer_amis.append('kali_machine')

            for packer_ami in packer_amis:
                self.log.info("Generate new Packer AMI packer-" + packer_ami + "-" + self.config['key_name'] + ". This can take some time.")
                template = 'packer/' + packer_ami +'/packer.json'
                template_vars = self.config
                (ret, out, err) = self.p.build(template,var=template_vars)
                if ret:
                    self.log.error("ERROR: " + str(out))
                    sys.exit(1)
                self.log.info("successfully generated Packer AMI packer-" + packer_ami + "-" + self.config['key_name'])

        #self.build_terraform()
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
        pass


    def resume(self):
        pass


    def simulate(self, target, simulation_techniques):
        pass


    def search(self, search_name):
        pass


    def list_machines(self):
        pass


    def list_searches(self):
        pass


from packerpy import PackerExecutable
from jinja2 import Environment, FileSystemLoader
from modules import aws_service
import sys 


class PackerController():

    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.p = PackerExecutable("/usr/local/bin/packer")
        self.packer_amis = []
        self.packer_amis.append('splunk-server')
        if self.config['phantom_server']=='1':
            self.packer_amis.append('phantom-server')
        if self.config['kali_machine']=='1':
            self.packer_amis.append('kali_machine')
        if self.config['windows_domain_controller']=='1':
            self.read_and_write_userdata_file()
            self.packer_amis.append('windows-domain-controller')
        if self.config['windows_server']=='1':
            self.read_and_write_userdata_file()
            self.packer_amis.append('windows-server')
        if self.config['windows_client']=='1':
            self.read_and_write_userdata_file()
            self.packer_amis.append('windows-client')

    def build_amis(self):
        self.log.info("[action] > build AMIs\n")
        for packer_ami in self.packer_amis:
            self.log.info("Generate new Packer AMI packer-" + packer_ami + "-" + self.config['key_name'] + ". This can take some time.")
            template = 'packer/' + packer_ami +'/packer.json'
            template_vars = self.config
            template_vars['splunk_indexer_ip'] = self.config['splunk_server_private_ip']
            (ret, out, err) = self.p.build(template,var=template_vars)
            if ret:
                self.log.error("ERROR: " + str(out))
                sys.exit(1)
            self.log.info("successfully generated Packer AMI packer-" + packer_ami + "-" + self.config['key_name'])


    def read_and_write_userdata_file(self):
        j2_env = Environment(loader=FileSystemLoader('packer/script'),trim_blocks=True)
        template = j2_env.get_template('userdata.ps1.j2')
        userdata_file = template.render(self.config)
        with open('packer/script/userdata.ps1', 'w') as file:
            file.write(userdata_file)


    def destroy_amis(self):
        aws_service.deregister_images(self.packer_amis, self.config, self.log)

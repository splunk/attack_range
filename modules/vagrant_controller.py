import ansible_runner
import sys
import os
import yaml
import vagrant

from tabulate import tabulate
from jinja2 import Environment, FileSystemLoader
from modules import splunk_sdk

from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController
from modules.purplesharp_simulation_controller import PurplesharpSimulationController


class VagrantController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)

    def build(self) -> None:

        self.logger.info("[action] > build\n")
        vagrantfile = 'Vagrant.configure("2") do |config| \n \n'

        if self.config['phantom_server']['phantom_server'] == "1":
            vagrantfile += self.read_vagrant_file('phantom_server/Vagrantfile')
            vagrantfile += '\n\n'            

        vagrantfile += self.read_vagrant_file('splunk_server/Vagrantfile')
        vagrantfile += '\n\n'

        for idx, x in enumerate(self.config['windows_servers']):
            vagrantfile += self.read_vagrant_file_array('windows_server/Vagrantfile', x, idx)
            vagrantfile += '\n\n'

        for idx, x in enumerate(self.config['linux_servers']):
            vagrantfile += self.read_vagrant_file_array('linux_server/Vagrantfile', x, idx)
            vagrantfile += '\n\n'

        if self.config['kali_server']['kali_server'] == "1":
            vagrantfile += self.read_vagrant_file('kali_server/Vagrantfile')
            vagrantfile += '\n\n'  

        vagrantfile += '\nend'
        with open('vagrant/Vagrantfile', 'w') as file:
            file.write(vagrantfile)
        
        v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False, quiet_stderr=False)
        try:
            v1.up(provision=True, provider="virtualbox")
        except:
            self.logger.error("vagrant failed to build")
            sys.exit(1)

        self.show()
        self.logger.info("attack_range has been built using vagrant successfully")
        

    def read_vagrant_file(self, path):
        j2_env = Environment(loader=FileSystemLoader('vagrant'),trim_blocks=True)
        template = j2_env.get_template(path)
        vagrant_file = template.render(
            config = self.config
        )
        return vagrant_file

    def read_vagrant_file_array(self, path, server, count):
        j2_env = Environment(loader=FileSystemLoader('vagrant'),trim_blocks=True)
        template = j2_env.get_template(path)
        vagrant_file = template.render(
            config = self.config,
            server = server,
            count = count
        )
        return vagrant_file    

    def destroy(self) -> None:
        self.logger.info("[action] > destroy\n")
        v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False)
        v1.destroy()
        self.logger.info("attack_range has been destroy using vagrant successfully")

    def stop(self) -> None:
        self.logger.info("[action] > stop\n")
        v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False)
        v1.halt()

    def resume(self) -> None:
        self.logger.info("[action] > resume\n")
        v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False)
        v1.up()

    def packer(self, image_name) -> None:
        pass

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
        v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False)
        result = v1.status()
        instances = []
        messages = []
        for status in v1.status():
            instances.append([status.name, status.state])
            if status.name.startswith("ar-splunk"):
                if self.config["splunk_server"]["install_es"] == "1":
                    messages.append("\nAccess Splunk via:\n\tWeb > https://192.168.56.12:8000\n\tSSH > cd vagrant & vagrant ssh " + status.name + " \n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                else:
                    messages.append("\nAccess Splunk via:\n\tWeb > http://192.168.56.12:8000\n\tSSH > cd vagrant & vagrant ssh " + status.name + " \n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
                messages.append("\nAccess Guacamole via:\n\tWeb > http://192.168.56.12:8080/guacamole" + "\n\tusername: Admin \n\tpassword: " + self.config['general']['attack_range_password'])
            elif status.name.startswith("ar-phantom"):
                messages.append("\nAccess Phantom via:\n\tWeb > https://192.168.56.13:8443 \n\tSSH > cd vagrant & vagrant ssh " + status.name + " \n\tusername: admin \n\tpassword: " + self.config['general']['attack_range_password'])
            elif status.name.startswith("ar-win"):
                messages.append("\nAccess Windows via:\n\tRDP > rdp://localhost:" + str(5389 + int(status.name[-1])) + " \n\tusername: Administrator \n\tpassword: " + self.config['general']['attack_range_password'])
            elif status.name.startswith("ar-linux"):
                messages.append("\nAccess Linux via:\n\tSSH > cd vagrant & vagrant ssh " + status.name)
            elif status.name.startswith("ar-kali"):
                messages.append("\nAccess Kali via:\n\tSSH > cd vagrant & vagrant ssh " + status.name)

        messages.append("\n")

        print(tabulate(instances, headers=['Name', 'Status']))
        for msg in messages:
            print(msg)


    def dump(self, dump_name, search, earliest, latest) -> None:
        self.logger.info("Dump log data")
        dump_search = "search " + search + " earliest=-" + earliest + " latest=" + latest + " | sort 0 _time"
        self.logger.info("Dumping Splunk Search: " + dump_search)
        out = open(os.path.join(os.path.dirname(__file__), "../" + dump_name), 'wb')

        splunk_sdk.export_search('localhost',
                                    s=dump_search,
                                    password=self.config['general']['attack_range_password'],
                                    out=out)
        out.close()
        self.logger.info("[Completed]")

    def replay(self, file_name, index, sourcetype, source) -> None:
        ansible_vars = {}
        ansible_vars['file_name'] = file_name
        ansible_vars['ansible_user'] = 'vagrant'
        ansible_vars['ansible_ssh_private_key_file'] = 'vagrant/.vagrant/machines/ar-splunk-' + self.config['general']['key_name'] + '-' + self.config['general']['attack_range_name'] + '/virtualbox/private_key'
        ansible_vars['attack_range_password'] = self.config['general']['attack_range_password']
        ansible_vars['ansible_port'] = 2222
        ansible_vars['sourcetype'] = sourcetype
        ansible_vars['source'] = source
        ansible_vars['index'] = index

        cmdline = "-i %s, -u %s" % ('localhost', ansible_vars['ansible_user'])
        runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                    cmdline=cmdline,
                                    roles_path=os.path.join(os.path.dirname(__file__), 'ansible/roles'),
                                    playbook=os.path.join(os.path.dirname(__file__), 'ansible/data_replay.yml'),
                                    extravars=ansible_vars)

    def create_remote_backend(self, backend_name) -> None:
        self.logger.error("Command not supported with local provider.")
        sys.exit(1)

    def delete_remote_backend(self, backend_name) -> None:
        self.logger.error("Command not supported with local provider.")
        sys.exit(1)

    def init_remote_backend(self, backend_name) -> None:
        self.logger.error("Command not supported with local provider.")
        sys.exit(1)
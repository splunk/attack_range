import ansible_runner
import sys
import os
import yaml
import vagrant

from jinja2 import Environment, FileSystemLoader

from modules.attack_range_controller import AttackRangeController
from modules.art_simulation_controller import ArtSimulationController
from modules.purplesharp_simulation_controller import PurplesharpSimulationController


class VagrantController(AttackRangeController):

    def __init__(self, config: dict):
        super().__init__(config)

    def build(self) -> None:
        self.logger.info("[action] > build\n")
        vagrantfile = 'Vagrant.configure("2") do |config| \n \n'
        vagrantfile += self.read_vagrant_file('splunk_server/Vagrantfile')
        vagrantfile += '\n\n'

        for idx, x in enumerate(self.config['windows_servers']):
            vagrantfile += self.read_vagrant_file_array('windows_server/Vagrantfile', x, idx)
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
        pass

    def resume(self) -> None:
        pass

    def packer(self, image_name) -> None:
        pass

    def simulate(self, engine, target, technique, playbook) -> None:
        pass

    def show(self) -> None:
        pass

    def dump(self, dump_name, search, earliest, latest) -> None:
        pass

    def replay(self, file_name, index, sourcetype, source) -> None:
        pass
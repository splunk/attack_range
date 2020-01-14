
from modules.IEnvironmentController import IEnvironmentController
from jinja2 import Environment, FileSystemLoader
import vagrant


class VagrantController(IEnvironmentController):


    def __init__(self, config, log):
        super().__init__(config, log)

        vagrantfile = 'Vagrant.configure("2") do |config| \n \n'
        vagrantfile += self.read_vagrant_file('splunk_server/Vagrantfile')
        vagrantfile += '\n\n'
        if config['windows_10'] == '1':
            vagrantfile += self.read_vagrant_file('windows10/Vagrantfile')
            vagrantfile += '\n\n'
        vagrantfile += '\nend'
        with open('vagrant/Vagrantfile', 'w') as file:
            file.write(vagrantfile)


    def read_vagrant_file(self, path):
        j2_env = Environment(loader=FileSystemLoader('vagrant'),trim_blocks=True)
        template = j2_env.get_template(path)
        vagrant_file = template.render(self.config)
        return vagrant_file


    def build(self):
        self.log.info("building splunk-server and windows10 workstation boxes WARNING MAKE SURE YOU HAVE 8GB OF RAM free otherwise you will have a bad time")
        self.log.info("[action] > build\n")
        v1 = vagrant.Vagrant('vagrant/', quiet_stdout=False)
        v1.up(provision=True)
        self.log.info("attack_range has been built using vagrant successfully")


    def destroy(self):
        pass


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

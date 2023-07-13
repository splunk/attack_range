
import ansible_runner
import os
import shutil

from modules.simulation_controller import SimulationController
from modules import aws_service, azure_service


class PurplesharpSimulationController(SimulationController):

    def simulate(self, target, technique, playbook) -> None:
        if self.config['general']['cloud_provider'] == 'aws':
            target_public_ip = aws_service.get_single_instance_public_ip(target, self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region'])
            ansible_user = 'Administrator'
            ansible_port = 5985

        elif self.config['general']['cloud_provider'] == 'azure':
            target_public_ip = azure_service.get_instance(target, self.config['general']['key_name'], self.config['general']['attack_range_name'])['public_ip']
            ansible_user = 'AzureAdmin'
            ansible_port = 5985

        elif self.config['general']['cloud_provider'] == 'local':
            target_public_ip = 'localhost'
            ansible_user = 'Administrator'
            ansible_port = 5985 + int(target[-1])

        technique = technique.replace(" ","")

        run_simulation_playbook = False
        simulation_playbook = ''
        if playbook:
            run_simulation_playbook = True
            simulation_playbook = playbook

        if "win" in target:
            runner = ansible_runner.run(
                private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                cmdline=str('-i ' + target_public_ip + ', '),
                roles_path=os.path.join(os.path.dirname(__file__), 'ansible/roles'),
                playbook=os.path.join(os.path.dirname(__file__), 'ansible/purplesharp.yml'),
                extravars= {
                    'ansible_port': ansible_port, 
                    'ansible_connection': 'winrm',
                    'ansible_winrm_server_cert_validation': 'ignore',
                    'ansible_user': ansible_user, 
                    'ansible_password': self.config['general']['attack_range_password'],
                    'run_simulation_playbook': run_simulation_playbook,
                    'simulation_playbook': simulation_playbook,
                    'techniques': technique,
                },
                verbosity=0
            )

        elif "linux" in target:
            print("ERROR: Linux is not supported in Purple Sharp.")
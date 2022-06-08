
import ansible_runner
import os
import shutil

from modules.simulation_controller import SimulationController
from modules import aws_service, azure_service


class ArtSimulationController(SimulationController):

    def simulate(self, target, technique) -> None:
        if 'aws' in self.config:
            target_public_ip = aws_service.get_single_instance_public_ip(target, self.config['general']['key_name'], self.config['general']['attack_range_name'], self.config['aws']['region'])
            ansible_user = 'Administrator'
            private_key_path = self.config['aws']['private_key_path']

        elif 'azure' in self.config:
            target_public_ip = azure_service.get_instance(target, self.config['general']['key_name'], self.config['general']['attack_range_name'])['public_ip']
            ansible_user = 'AzureAdmin'
            private_key_path = self.config['azure']['private_key_path']

        techniques = technique.split(',')

        if "win" in target:
            runner = ansible_runner.run(
                private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                cmdline=str('-i ' + target_public_ip + ', '),
                roles_path=os.path.join(os.path.dirname(__file__), 'ansible/roles'),
                playbook=os.path.join(os.path.dirname(__file__), 'ansible/atomic_red_team.yml'),
                extravars= {
                    'ansible_port': 5985, 
                    'ansible_connection': 'winrm',
                    'ansible_winrm_server_cert_validation': 'ignore',
                    'techniques': techniques, 
                    'ansible_user': ansible_user, 
                    'ansible_password': self.config['general']['attack_range_password'], 
                    'art_repository': self.config['simulation']['atomic_red_team_repo'], 
                    'art_branch': self.config['simulation']['atomic_red_team_branch']
                },
                verbosity=0
            )

        elif "linux" in target:
            runner = ansible_runner.run(
                private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                cmdline=str('-u ubuntu --private-key ' + private_key_path + ' -i ' + target_public_ip + ', '),
                roles_path=os.path.join(os.path.dirname(__file__), 'ansible/roles'),
                playbook=os.path.join(os.path.dirname(__file__), 'ansible/atomic_red_team.yml'),
                extravars= {
                    'ansible_python_interpreter': '/usr/bin/python3',
                    'techniques': techniques, 
                    'art_repository': self.config['simulation']['atomic_red_team_repo'], 
                    'art_branch': self.config['simulation']['atomic_red_team_branch']
                },
                verbosity=0
            )

        shutil.rmtree(os.path.join(os.path.dirname(__file__), '../artifacts'))
        shutil.rmtree(os.path.join(os.path.dirname(__file__), '../env'))
import os
import collections
import sys

from modules.yml_reader import YmlReader


class ConfigHandler:

    @classmethod
    def read_config(self, config_path: str) -> dict:
        yml_dict_default = YmlReader.load_file(os.path.join(os.path.dirname(__file__), '../configs/attack_range_default.yml'))
        yml_dict = YmlReader.load_file(os.path.join(os.path.dirname(__file__), '../', config_path))

        parent_keys = ['general', 'aws', 'azure', 'splunk_server', 'phantom_server', 'kali_server', 'nginx_server', 'simulation', 'zeek_server']

        for parent_key in parent_keys:
            if parent_key in yml_dict:
                for key in yml_dict[parent_key]:
                    yml_dict_default[parent_key][key] = yml_dict[parent_key][key]

        parent_keys_servers = ['windows_servers', 'linux_servers']

        for parent_key in parent_keys_servers:
            if parent_key not in yml_dict:
                yml_dict_default[parent_key] = []
            elif not yml_dict[parent_key]:
                yml_dict_default[parent_key] = []
            else:
                i = 0
                yml_dict_default[parent_key] = []
                for windows_server in yml_dict[parent_key]:
                    yml_dict_default[parent_key].append(yml_dict_default[parent_key + '_default'].copy())
                    for key in windows_server:
                        yml_dict_default[parent_key][i][key] = windows_server[key]
                    i = i + 1

        yml_dict_default.pop('windows_servers_default')
        yml_dict_default.pop('linux_servers_default')

        return yml_dict_default

    @classmethod
    def validate_config(self, config: dict) -> None:
        if config['general']['attack_range_password'] in ['ChangeMe123!', 'Pl3ase-k1Ll-me:p1']:
            print("ERROR: please change attack_range_password in attack_range.yml")
            sys.exit(1)      

        i = 0
        for windows_server in config['windows_servers']:
            if windows_server['create_domain'] == "0" and windows_server['bad_blood'] == "1":
                print("ERROR: bad_blood is only allowed on the domain controller.")
                sys.exit(1) 

            if (i > 0) and windows_server['create_domain'] == "1":
                print("ERROR: create_domain=1 is only allowed for the first windows server in the list windows_servers.")
                sys.exit(1)                      
            i = i + 1

        # windows 10 and 11 only allowed in Azure

        if config['nginx_server']['nginx_server'] == "1" and config['general']['cloud_provider'] == "azure":
            print("ERROR: Nginx Server not supported in Azure.")
            sys.exit(1)         

        if config['kali_server']['kali_server'] == "1" and config['general']['cloud_provider'] == "azure":
            print("ERROR: Kali Server not supported in Azure.")
            sys.exit(1)   

        if config['zeek_server']['zeek_server'] == "1" and config['general']['cloud_provider'] == "azure":
            print("ERROR: Zeek Server not supported in Azure.")
            sys.exit(1)   

        if config['general']['carbon_black_cloud'] == "1" and config['general']['cloud_provider'] == "azure":
            print("ERROR: Carbon Black Cloud or Crowdstrike Falcon can only used in AWS.")
            sys.exit(1)
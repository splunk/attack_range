"""
author: Teoderick Contreras
email: tccontreras@splunk.com
description: a utility class for several helper functions for echo-attack utility tool:
 - analytic story
 - detection name
 - detection guid id
 - Mitre attack Technique ID
 - detection name list in a file
"""

import os
import sys
import yaml
import platform
from pathlib import Path
from colorama import Fore, Back, Style, init
import datetime
import json
import requests
import subprocess
import typer
import uuid
import re
from collections import defaultdict
from urllib.parse import urlparse, urlunparse, unquote

from utility.color_print import ColorPrint
import json

class UtilityHelper:

    def __init__(self):
        self.curdir = os.getcwd()
        self.config_file_path = os.path.join(self.curdir, "configuration", "config.yml")
        self.home_path = Path.home()
        self.processed_attack_data_uuid = []
        self.header_val = ""
        return
    
    def get_header_val(self):
        return self.header_val
    #############################################
    ### config helper functions
    #############################################
    def get_config_file_path(self)->str:
        return self.config_file_path 
    
    def load_config(self)->str:
        with open(self.get_config_file_path(), "r") as file:
            return yaml.safe_load(file)

    def read_config_settings(self, setting_field:str, key_tag="settings")->str:
        cfg = self.load_config()
        config_field = cfg[key_tag][setting_field]
        return config_field
    
    #############################################
    ### helper functions
    #############################################
    def clear_screen(self)->None:
        """Clear the console screen based on the operating system."""
        if platform.system() == "Windows":
            os.system("cls")   ## Windows
        else:
            os.system("clear") ## macOS/Linux

        return
    
    def get_time_stamps(self)->str:
        """get the current timestamps"""
        timestamps = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return
    
    def show_banner(self)->None:

        banner = r"""
                 ________________
                |'-.--._ _________:
                |  /    |  __    __\   
                | |  _  | [\_\= [\_\_         ████████╗ ██████╗ ████████╗ █████╗ ██╗      ██████╗ ███████╗██████╗ ██╗      █████╗ ██╗   ██╗    ██╗ ██╗
                | |.' '. \...........|        ╚══██╔══╝██╔═══██╗╚══██╔══╝██╔══██╗██║      ██╔══██╗██╔════╝██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝    ╚██╗╚██╗ 
                | ( <)  ||: █ █ █ █ :|_          ██║   ██║   ██║   ██║   ███████║██║█████╗██████╔╝█████╗  ██████╔╝██║     ███████║ ╚████╔╝      ╚██╗╚██╗
                \ '._.'█| :.....: |_(o █ █       ██║   ██║   ██║   ██║   ██╔══██║██║╚════╝██╔══██╗██╔══╝  ██╔═══╝ ██║     ██╔══██║  ╚██╔╝       ██╔╝██╔╝
                '-\_   \ .------./               ██║   ╚██████╔╝   ██║   ██║  ██║███████╗ ██║  ██║███████╗██║     ███████╗██║  ██║   ██║       ██╔╝██╔╝ 
                _   \   ||.---.||  _             ╚═╝    ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝       ╚═╝ ╚═╝ 
                / \  '-._|/|x~~|x | \        
                / \  '-._|/|x~~|x | \         by: @tccontre18 - Splunk Threat Research Team [STRT]
                (| []=.--[===[()]===[) |      ███████████████████████████████████████████████████████████████████████████████████████████████████████████═╗ 
                <\_/  \_______/ _.' /_/.       ╚══════════════════════════════════════════════════════════════════════════════════════════════════════════╝
                ///            (_/_/.         
                |\\            [\\.              
                ||:|           | I|
                :/\:            ([])
                ([])             [|
                ||              |\_
                _/_\_            [ -'-.__
        snd <]   \>            \_____.>
                \__/          ___Br3akp0int_]

        """ 
        self.clear_screen()

        ColorPrint.print_cyan_fg(banner)

        return
    
    def header_divider(self, header:str, tag:str="...")->str:
        timestamp = f"[ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ]==> [+][. TOTAL-REPLAY: {tag}]: ..."
        header_div = f"""
 ╔══════════════════════════════════════════════════════════════════ [ {header} ] ══════════════════════════════════════════════════════════════════
 ║
 ╚═{timestamp}
    """
        return header_div

    def footer_divider(self,footer:str):
        timestamp = f"[ {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ]==> [+][.    END]: ..."

        footer_div = f"""
 ╔═{timestamp}
 ╚══════════════════════════════════════════════════════════════════ [ {footer} ] ═══════════════════════════════════════════════════════════════════
    """
        return footer_div
    
    def load_environment_variables(self)->dict:
        """Load required environment variables for Splunk connection."""
        ColorPrint.print_info_fg("[+][.  INFO]: ... Checking SPLUNK HOST and HEC_TOKEN ENV VARIABLE ...")
        required_vars = ['SPLUNK_HOST', 'SPLUNK_HEC_TOKEN']
        env_vars = {}
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                ColorPrint.print_error_fg(f"[-][. ERROR]: ... Environment variable {var} is required but not set")
                return {}
                #raise ValueError(f"[-][. ERROR]: Environment variable {var} is required but not set")
            env_vars[var.lower().replace('splunk_', '')] = value
        return env_vars

    def normalized_args_tolist(self, input_args:str)->list:
        return [i.strip() for i in input_args.split(',')] 

    def check_total_replay_setup(self)->str:

        header = ""

        attack_range_switch = self.read_config_settings("attack_range_version_on")
        attack_data_switch = self.read_config_settings("attack_data_version_on")

        if attack_range_switch == True and attack_data_switch == False:
            header = "TOTAL_REPLAY_ATTACK_RANGE_ON"
        elif attack_range_switch == False and attack_data_switch == True:
            header = "TOTAL_REPLAY_ATTACK_DATA_ON"
        else:
            header = ""
        return header

    def process_replay_attack_data_by_file_name(self, tag:str, normalized_args_list:list, index_value:str, generated_guid:str)->None:
        """main function in replaying attack data base on Splunk detection filename"""

        ### check which setup version of total-replay should be enable. attack range or attack data
        self.header_val  = ""
        self.header_val  = self.check_total_replay_setup()

        if self.header_val  == "":
            ColorPrint.print_error_fg("[-][. ERROR]: ... You cannot enable/disable both version of TOTAL-REPLAY in config.yml. Choose either Attack Range or Attack Data version")
            return
        else:
            ColorPrint.print_cyan_fg(self.header_divider(self.header_val, tag))

            ColorPrint.print_info_fg(f'[+][.  INFO]: ... Enumerating detection .yml file name ... []')
            security_content_dir_path = self.read_config_settings("security_content_detection_path")

            if not os.path.isdir(os.path.expanduser(security_content_dir_path)):
                ColorPrint.print_error_fg("[+][. ERROR]: The security Content folder path in config is invalid or not exist.")
                return
            

            ctr= 1
            search_found_list = []
            for field_name in normalized_args_list:

                ### skipped if the inputted string has no file extension or not a .yml file
                if not field_name.endswith(".yml"):
                    continue
                
                found_flag = False
                needed_replay_yaml_field = {}

                for roots, dirs, files in os.walk(os.path.expanduser(security_content_dir_path)):

                    ### skip deprecated directories
                    if dirs == "deprecated":
                        continue
                    
                    ### break the loop once we found the needed field name
                    if found_flag:
                        break

                    ### enumerate the files in the directory
                    for file in files:
                        
                        if file.lower() == field_name.lower():
                            ColorPrint.print_success_fg(f"[+][SUCCESS]: ... SEARCH FOUND -> [ {file} ]")
                            file_path = os.path.join(roots, file)
                            
                            yaml_data = self.read_yaml_file(file_path)

                            ### check if file content is empty or invalid 
                            if yaml_data == None:
                                ColorPrint.print_warning_fg(f"[!][WARNING]: ... Skipping empty or invalid YAML file: {file_path}")
                                continue

                            needed_replay_yaml_field = self.create_metadata_cache(yaml_data)
                            search_found_list.append(needed_replay_yaml_field)
                            found_flag = True
            
            ColorPrint.print_info_fg(f"[+][.  INFO]: ... Total filtered detections: {len(search_found_list)} ")

                
            ### generate uid for caching purposes of replay data

            for needed_replay_yaml_field in search_found_list:

                ### get the attack data url link
                if "attack_data_link" in needed_replay_yaml_field:
                    attack_data_link = needed_replay_yaml_field["attack_data_link"]
                else:
                    continue

                ### generate replay yaml output folder
                output_base_dir = os.path.join(self.curdir, self.read_config_settings('output_dir_name'))
                self.generate_output_dir(output_base_dir)
                
                attack_data_timestamp_dir_path = os.path.join(output_base_dir, datetime.date.today().strftime("%Y-%m-%d"))
                escu_detection_guid = needed_replay_yaml_field['id']

                ColorPrint.print_info_fg(f"[+][.  INFO]: ... Downloading attack data ... item:{ctr}")
                attack_datasets_path = self.download_attack_data(attack_data_link, needed_replay_yaml_field, generated_guid, attack_data_timestamp_dir_path, escu_detection_guid)                    

                ### update the total-replay cache yaml file
                needed_replay_yaml_field['attack_data_output_file_path'] = attack_datasets_path
                
                if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON": 
                    needed_replay_yaml_field = self.locate_associated_attack_data_yaml_file(attack_data_link, attack_datasets_path, needed_replay_yaml_field)
                if not needed_replay_yaml_field:
                    return
                
                ### dropped the replay yaml cache
                replayed_yaml_cache_path = os.path.join(attack_data_timestamp_dir_path, generated_guid, self.read_config_settings('replayed_yaml_cache_dir_name'))
                self.generate_output_dir(replayed_yaml_cache_path)

                cache_replay_yaml_file_path = os.path.join(replayed_yaml_cache_path, needed_replay_yaml_field['id']+ "_" + self.read_config_settings('cache_replay_yaml_name'))
                self.dump_yaml_file(cache_replay_yaml_file_path, needed_replay_yaml_field)

                ### comment me if you dont want to see the replay_cache yml file
                if self.read_config_settings('debug_print'):
                    ColorPrint.print_yellow_fg(Style.DIM + self.header_divider("TOTAL-REPLAY CACHE YAML FILE", tag))
                    ColorPrint.print_yellow_fg(Style.DIM + f"[+] ... \n{json.dumps(needed_replay_yaml_field, indent=4)}")
                    ColorPrint.print_yellow_fg(Style.DIM + self.footer_divider("TOTAL-REPLAY CACHE YAML FILE"))

                ### simple logic to avoid replaying the same attack data again and again (note: only applicable in attack_data_version)
                if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON": 
                    if needed_replay_yaml_field['attack_data_uuid'] in self.processed_attack_data_uuid:
                        ColorPrint.print_info_fg(Style.BRIGHT + f"[+][.  INFO]: ... ATTACK_DATA UUID: {needed_replay_yaml_field['attack_data_uuid']} has already been replayed.")
                        ctr+=1
                        continue                

                    self.processed_attack_data_uuid.append(needed_replay_yaml_field['attack_data_uuid'])

                if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON":
                    self.attack_data_replay_cmd(needed_replay_yaml_field, index_value)
                elif self.header_val == "TOTAL_REPLAY_ATTACK_RANGE_ON":
                    self.attack_range_replay_cmd(needed_replay_yaml_field, index_value)
                else:
                    raise ValueError(f"Unknown Total-Replay Switch Version: {self.header_val}")


                ctr+=1
                ColorPrint.print_magenta_fg("\n[+]" + "█" * 160 + "\n")

        ColorPrint.print_cyan_fg(self.footer_divider(self.header_val))               

        return
    
    def dump_yaml_file(self, file_path:str, data:str):

        ### generate cache data
        with open(file_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        return

    def generate_output_dir(self, dir_name:str):
        """generate the base output folder for total-replay cache data"""

        ### if not exist create output directory
        if not os.path.isdir(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            ColorPrint.print_success_fg(f"[+][SUCCESS]: ... {dir_name} folder created!")
        return
        
    def download_via_attack_range(self, attack_data_link:str, attack_data_timestamp_dir_path:str, generated_guid:str, escu_detection_guid:str)->str:
        """download needed raw attack data via attack range feature"""

        guid_dir_path = os.path.join(attack_data_timestamp_dir_path, generated_guid, escu_detection_guid)
        self.generate_output_dir(guid_dir_path)

        ## download the file with streaming enable
        response = requests.get(attack_data_link, stream=True)
        response.raise_for_status() # Raise an error for bad responses (e.g., 404, 403)

        attack_data_file_path = os.path.join(guid_dir_path,os.path.basename(attack_data_link))

        with open(attack_data_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        ColorPrint.print_success_fg(f"[+][SUCCESS]: ... file {os.path.basename(attack_data_link)} downloaded successfully")  

        
        return attack_data_file_path

    def attack_range_replay_cmd(self, needed_replay_yaml_field:dict, index_value:str)->bool:
        """replay the attack_data logs via attack range replay feature"""

        if not os.path.isdir(os.path.expanduser(self.read_config_settings('attack_range_dir_path'))):
            ColorPrint.print_error_fg("[+][. ERROR]: The attack range folder path in config is invalid or not exist.")
            return False

        attack_range_py_file_path = os.path.join(os.path.expanduser(self.read_config_settings('attack_range_dir_path')), self.read_config_settings('attack_range_py_name'))

        error_terms = ["error", "Failed to connect","unreacheable=1", "timed out", "exception","fatal"]
        ### setup Command arguments
        attack_data_file_path = needed_replay_yaml_field['attack_data_output_file_path']
        attack_data_source = needed_replay_yaml_field['attack_data_source']
        attack_data_source_type = needed_replay_yaml_field['attack_data_sourcetype']
        python_interpreter_name = self.read_config_settings('python_interpreter_name')

        command = ["poetry", "run", f"{python_interpreter_name}", f"{attack_range_py_file_path}",  "replay", "-fn", f"{attack_data_file_path}", "--source", f"{attack_data_source}", "--sourcetype", f"{attack_data_source_type}", "--index", f"{index_value}"]
        
        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,text=True)
            output = result.stdout.strip()

            ### comment this if you dont want to see the replay stdout
            if self.read_config_settings('debug_print'):
                ColorPrint.print_green_fg(Style.DIM + self.header_divider("ATTACK DATA REPLAY SUMMARY"))
                ColorPrint.print_green_fg(Style.DIM + f"[+] ...\n{output}\n")
                ColorPrint.print_green_fg(Style.DIM + self.footer_divider("ATTACK DATA REPLAY SUMMARY"))
            
            if any(term.lower() in str(result).lower() for term in error_terms):
                ColorPrint.print_error_fg(Style.BRIGHT + f"[+][. ERROR]: ... [{needed_replay_yaml_field['name']}] replayed Failed")
                return False
            else:
                ColorPrint.print_success_fg(Style.BRIGHT + f"[+][SUCCESS]: ... [{needed_replay_yaml_field['name']}] replayed succesfully")
                return True  # If successful, return True
        except subprocess.CalledProcessError as e:
            # If an error occurs, print the error and return False
            output = e.stdout.strip() if e.stdout else "No output"

            ColorPrint.print_error_fg(f"[-][. ERROR]: ... running command: {e}")
            ColorPrint.print_error_fg(f"[-][. ERROR]: ... running command: {output}")
            return False
    
    def download_via_attack_data(self, attack_data_link:str, attack_data_timestamp_dir_path:str, generated_guid:str)->str:
        """download needed raw attack data via attack data feature"""
        
        ### generate a unique guid folder path
        guid_dir_path = os.path.join(attack_data_timestamp_dir_path, generated_guid)
        self.generate_output_dir(guid_dir_path)

        ### verify if the string contain url scheme 
        p = urlparse(attack_data_link)
        if not p.scheme or not p.netloc:
            raise ValueError(f"[-][. ERROR]: ... Unsupported GitHub URL format: {attack_data_link}")
        
        m, datasets_path = str(p.path).split("master/")

        # Find the Git repository root
        repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"],text=True).strip()

        git_lfs_cmd = ["git", "lfs", "pull", f"--include={datasets_path}"]
        ColorPrint.print_info_fg(f"[+][.  INFO]: ... command: {" ".join(git_lfs_cmd)}")

        ### execute the git command process
        try:
            result = subprocess.run(git_lfs_cmd, check=True, cwd=repo_root, capture_output=True, text=True)
            ColorPrint.print_success_fg(f"[+][SUCCESS]: ... Git Command succeeded! attack data: {datasets_path} ==> downloaded succesfully!")
        except subprocess.CalledProcessError as e:
            ColorPrint.print_error_fg("[-][. ERROR]: ... Command failed!")
            ColorPrint.print_error_fg("[-][. ERROR]: ... Exit code:", e.returncode)
            ColorPrint.print_error_fg("[-][. ERROR]: ... Stdout:", e.stdout)
            ColorPrint.print_error_fg("[-][. ERROR]: ... Stderr:", e.stderr) 

        return datasets_path
     
    def download_attack_data(self, attack_data_link:str, needed_yaml_field_cache:dict, generated_guid:str, attack_data_timestamp_dir_path:str, escu_detection_guid:str)->str:
        """download attack data raw logs """

        if self.header_val == "TOTAL_REPLAY_ATTACK_RANGE_ON":
            attack_datasets_path = self.download_via_attack_range(attack_data_link, attack_data_timestamp_dir_path, generated_guid, escu_detection_guid)
        if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON":
            attack_datasets_path = self.download_via_attack_data(attack_data_link, attack_data_timestamp_dir_path, generated_guid)

        return attack_datasets_path

    def read_yaml_file(self, file_path:str)->dict:
        """Read a YAML file and return its content as a dictionary."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            ColorPrint.print_error_fg(f"[!] [ERROR]: File not found: {file_path}")
            return None
        except PermissionError:
            ColorPrint.print_error_fg(f"[!] [STATUS]: error ... permission denied: {file_path}")
            return None
        except yaml.YAMLError as e:
            ColorPrint.print_error_fg(f"[!] [ERROR]: Error reading YAML file {file_path}: {e}")
            return None

    def locate_associated_attack_data_yaml_file(self, attack_data_link:str, attack_datasets_path:str, needed_yaml_field_cache:dict)->dict:

        ### check and parsed the yml file associated with the attack data
        yml_name = os.path.basename(os.path.dirname(unquote(urlparse(attack_data_link).path)))

        ### locate the attack_data path in config
        if not os.path.isdir(os.path.expanduser(self.read_config_settings('attack_data_dir_path'))):
            ColorPrint.print_error_fg("[+][. ERROR]: The attack data folder path in config is invalid or not exist.")
            return {}
        
        attack_data_full_dir_path = os.path.join(os.path.expanduser(self.read_config_settings('attack_data_dir_path')), os.path.dirname(attack_datasets_path))

        ### enumerate all yaml file inside the attack data folder base on the attack_data_link in escu
        for file in os.listdir(attack_data_full_dir_path):
            if file.endswith((".yml", ".yaml")):
                yml_file_path = os.path.join(attack_data_full_dir_path, file)
                attack_data_yaml_buff = self.read_yaml_file(yml_file_path)
                
                ### this is to support the old and new attack data yaml format
                datasets = attack_data_yaml_buff.get("datasets", [])
                dataset = attack_data_yaml_buff.get("dataset", "")

                has_new_format = (
                    isinstance(datasets, list)
                    and len(datasets) > 0
                    and attack_datasets_path in datasets[0].get("path", "")
                )

                has_old_format = (
                    (isinstance(dataset, str) and attack_datasets_path in dataset)
                    or (isinstance(dataset, list) and dataset and attack_datasets_path in dataset[0])
                )

                if yml_name in file or has_new_format or has_old_format:
                    
                    needed_yaml_field_cache['attack_data_yml_file_path'] = yml_file_path
                    attack_id = attack_data_yaml_buff.get("id")
                    if attack_id:
                        needed_yaml_field_cache['attack_data_uuid'] = attack_data_yaml_buff['id']
                        ColorPrint.print_success_fg(f"[+][SUCCESS]: ... {file} ==> associated yml file extracted successfully")
                        break
                    else:
                        ColorPrint.print_warning_fg(f"[!][WARNING]: ... attack_data yaml field: [uuid] => not found!!")
                else:
                    continue           

        return needed_yaml_field_cache

    def create_metadata_cache(self, yaml_data: yaml) -> dict:
        """Create a metadata cache from the YAML data."""

        needed_replay_yaml_field = {
            "name": yaml_data.get("name", "Unknown"),
            "id": yaml_data.get("id", "Unknown"),
            "mitre_attack_id": yaml_data.get("tags", {}).get("mitre_attack_id", "Unknown"),
            "analytic_story": yaml_data.get("tags", {}).get("analytic_story", "Unknown"),
            "description": yaml_data.get("description", "No description available"),
            #"file_path": yaml_data.get("file_path", "Unknown")
        }

        # Checking for 'tests' key for handling 'attack_data' yaml field
        if "tests" in yaml_data:

            # Check if 'attack_data' is present and not empty
            if yaml_data["tests"]:
                test = yaml_data["tests"][0]  # First test in the list

                # Check for 'attack_data' key and that it's not empty
                if "attack_data" in test and test["attack_data"]:
                    attack_data = test["attack_data"][0]  # Assuming it's a list with at least one entry

                    # Adding the 'attack_data' fields to the cache dictionary
                    needed_replay_yaml_field["attack_data_link"] = attack_data.get("data", "N/A")
                    needed_replay_yaml_field["attack_data_source"] = attack_data.get("source", "N/A")
                    needed_replay_yaml_field["attack_data_sourcetype"] = attack_data.get("sourcetype", "N/A")

                else:
                    ColorPrint.print_warning_fg("[!][WARNING]: ... attack_data is empty or missing in the first test")
            else:
                ColorPrint.print_warning_fg("[!][WARNING]: ... no tests available in the YAML")
        else:
            ColorPrint.print_warning_fg("[!][WARNING]: ... no tests field in YAML data")

        return needed_replay_yaml_field
    
    def attack_data_replay_cmd(self, needed_replay_yaml_field:dict, index_value:str)->bool:
        """main function in replaying attack data in splunk server"""
        
        env_var = self.load_environment_variables()
        error_terms = ["error", "Failed to connect","unreacheable=1", "timed out", "exception","fatal"]
        ### setup Command arguments
        attack_data_file_path = needed_replay_yaml_field['attack_data_output_file_path']
        attack_data_source = needed_replay_yaml_field['attack_data_source']
        attack_data_source_type = needed_replay_yaml_field['attack_data_sourcetype']
        attack_data_uuid = needed_replay_yaml_field['attack_data_uuid']
        attack_data_yml_file_path = needed_replay_yaml_field['attack_data_yml_file_path']
        python_interpreter_name = self.read_config_settings('python_interpreter_name')


        if not os.path.isdir(os.path.expanduser(self.read_config_settings('attack_data_dir_path'))):
            ColorPrint.print_error_fg("[+][. ERROR]: The attack data folder path in config is invalid or not exist.")
            return False
        
        replay_path = os.path.join(os.path.expanduser(self.read_config_settings('attack_data_dir_path')), "bin","replay.py")

        command = ["poetry", "run", f"{python_interpreter_name}",  f"{replay_path}", "--index-override", f"{index_value}", "--source-override", f"{attack_data_source}", "--sourcetype-override", f"{attack_data_source_type}", "--host-uuid", f"{attack_data_uuid}", f"{attack_data_yml_file_path}"]
        ColorPrint.print_info_fg(f"[+][.  INFO]: ... {" ".join(command)}")

        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,text=True)
            output = result.stdout.strip()

            ### comment this if you dont want to see the replay stdout
            if self.read_config_settings('debug_print'):
                ColorPrint.print_green_fg(Style.DIM + self.header_divider("ATTACK DATA REPLAY SUMMARY"))
                ColorPrint.print_green_fg(Style.DIM + f"[+] ...\n{output}\n")
                ColorPrint.print_green_fg(Style.DIM + self.footer_divider("ATTACK DATA REPLAY SUMMARY"))

            if any(term.lower() in str(result).lower() for term in error_terms):
                ColorPrint.print_error_fg(Style.BRIGHT + f"[+][. ERROR]: ... [{needed_replay_yaml_field['name']}] replayed Failed")
                return False
            else:
                ColorPrint.print_success_fg(Style.BRIGHT + f"[+][SUCCESS]: ... [{needed_replay_yaml_field['name']}] replayed succesfully")
                return True  # If successful, return True
        except subprocess.CalledProcessError as e:
            # If an error occurs, print the error and return False
            output = e.stdout.strip() if e.stdout else "No output"

            ColorPrint.print_error_fg(f"[-][. ERROR]: ... running command: {e}")
            ColorPrint.print_error_fg(f"[-][. ERROR]: ... running command: {output}")
            return False


    def process_replay_attack_data(self, tag:str, normalized_args_list:list, index_value:str, generated_guid:str)->None:
        """main function in replaying attack data using ESCU metadata"""

        ### check which setup version of total-replay should be enable. attack range or attack data
        self.header_val  = ""
        self.header_val  = self.check_total_replay_setup()

        if self.header_val  == "":
            ColorPrint.print_error_fg("[-][. ERROR]: ... You cannot enable/disable both version of TOTAL-REPLAY in config.yml. Choose either Attack Range or Attack Data version")
            return
        else:
            ColorPrint.print_cyan_fg(self.header_divider(self.header_val, tag))

        ctr = 1
        search_found_list = [] 
        for field_name in normalized_args_list:

            ### skipped if the inputted string has file extension or not a .yml file
            if field_name.endswith(".yml"):
                continue

            needed_replay_yaml_field = {}
            search_found_list = self.search_security_content(tag, field_name)

            if not search_found_list:
                return
            
            ColorPrint.print_info_fg(f"[+][.  INFO]: ... Total filtered detections: {len(search_found_list)} ")

               
            for needed_replay_yaml_field in search_found_list:

                ### get the attack data url link
                if "attack_data_link" in needed_replay_yaml_field:
                    attack_data_link = needed_replay_yaml_field["attack_data_link"]
                else:
                    continue

                ### generate replay yaml output folder
                output_base_dir = os.path.join(self.curdir, self.read_config_settings('output_dir_name'))
                self.generate_output_dir(output_base_dir)
                
                attack_data_timestamp_dir_path = os.path.join(output_base_dir, datetime.date.today().strftime("%Y-%m-%d"))
                escu_detection_guid = needed_replay_yaml_field['id']

                ColorPrint.print_info_fg(f"[+][.  INFO]: ... Downloading attack data ... item:{ctr}")
                attack_datasets_path = self.download_attack_data(attack_data_link, needed_replay_yaml_field, generated_guid, attack_data_timestamp_dir_path, escu_detection_guid)

                ### update the total-replay cache yaml file
                needed_replay_yaml_field['attack_data_output_file_path'] = attack_datasets_path
                
                if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON": 
                    needed_replay_yaml_field = self.locate_associated_attack_data_yaml_file(attack_data_link, attack_datasets_path, needed_replay_yaml_field)
                if not needed_replay_yaml_field:
                    return

                ### dropped the replay yaml cache
                replayed_yaml_cache_path = os.path.join(attack_data_timestamp_dir_path, generated_guid, self.read_config_settings('replayed_yaml_cache_dir_name'))
                self.generate_output_dir(replayed_yaml_cache_path)

                cache_replay_yaml_file_path = os.path.join(replayed_yaml_cache_path, needed_replay_yaml_field['id']+ "_" + self.read_config_settings('cache_replay_yaml_name'))
                self.dump_yaml_file(cache_replay_yaml_file_path, needed_replay_yaml_field)

                ### comment me if you dont want to see the replay_cache yml file
                if self.read_config_settings('debug_print'):
                    ColorPrint.print_yellow_fg(Style.DIM + self.header_divider("TOTAL-REPLAY CACHE YAML FILE", tag))
                    ColorPrint.print_yellow_fg(Style.DIM + f"[+] ... \n{json.dumps(needed_replay_yaml_field, indent=4)}")
                    ColorPrint.print_yellow_fg(Style.DIM + self.footer_divider("TOTAL-REPLAY CACHE YAML FILE"))

                ### simple logic to avoid replaying the same attack data again and again
                if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON": 
                    if needed_replay_yaml_field['attack_data_uuid'] in self.processed_attack_data_uuid:
                        ColorPrint.print_info_fg(Style.BRIGHT + f"[+][.  INFO]: ... ATTACK_DATA UUID: {needed_replay_yaml_field['attack_data_uuid']} has already been replayed.")
                        ctr+=1
                        continue                

                    self.processed_attack_data_uuid.append(needed_replay_yaml_field['attack_data_uuid'])

                if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON":
                    self.attack_data_replay_cmd(needed_replay_yaml_field, index_value)
                elif self.header_val == "TOTAL_REPLAY_ATTACK_RANGE_ON":
                    self.attack_range_replay_cmd(needed_replay_yaml_field, index_value)
                else:
                    raise ValueError(f"Unknown Total-Replay Switch Version: {self.header_val}")
                    
                ctr+=1
                ColorPrint.print_magenta_fg("\n[+]" + "█" * 160 + "\n")

        ColorPrint.print_cyan_fg(self.footer_divider(self.header_val))                                    


        return

    def search_security_content(self, key_name: str, field_name:str)->list:
        """Function in parsing Splunk Security Content Repo"""

        ColorPrint.print_info_fg(f'[+][.  INFO]: ... processing => [ {field_name} ]')

        search_found_list = []

        found_flag = False

        needed_replay_yaml_field = {}
        security_content_dir_path = self.read_config_settings("security_content_detection_path")

        if not os.path.isdir(os.path.expanduser(security_content_dir_path)):
            ColorPrint.print_error_fg("[+][. ERROR]: The security Content folder path in config is invalid or not exist.")
            return []
        
        for root, dirs, files in os.walk(os.path.expanduser(security_content_dir_path)):
            ## skip deprecated folder
            if dirs == "deprecated":
                continue
            ## break the loop once we found the needed field value
            if found_flag:
                break
            
            for file in files:

                if file.endswith((".yaml",".yml")):
                    file_path = os.path.join(root, file)

                    yaml_data = self.read_yaml_file(file_path)

                    ### check if file content is empty or invalid 
                    if yaml_data is None:
                        ColorPrint.print_error_fg(f"[!] [STATUS]: [. ERROR] ... skipping empty or invalid YAML file: {file_path}")
                        continue
                    
                    if self.check_needed_yaml_field(key_name, field_name, yaml_data):
                        if key_name != "mitre_attack_id" and key_name != "analytic_story":
                            found_flag = True
                                
                        needed_replay_yaml_field = self.create_metadata_cache(yaml_data)
                        search_found_list.append(needed_replay_yaml_field)

        return search_found_list

    def check_needed_yaml_field(self, yaml_key_name:str, field_name:str, yaml_data:yaml)->bool:
        """Function for checking needed yaml fields per search type"""
        if yaml_key_name == "name":
            if yaml_data.get(yaml_key_name).lower() == field_name.lower():
                ColorPrint.print_success_fg(f"[+][SUCCESS]: ... found -> [ {yaml_data.get(yaml_key_name)} ]")
                return True
            
        elif yaml_key_name == "mitre_attack_id":
            if yaml_data['tags']:
                if "mitre_attack_id" in yaml_data['tags']:
                    if field_name.lower() in [i.lower() for i in yaml_data['tags']['mitre_attack_id']]:
                        return True
                    
        elif yaml_key_name == "analytic_story":
            if yaml_data['tags']:
                if "analytic_story" in yaml_data['tags']:
                    if field_name.lower() in [i.lower() for i in yaml_data['tags']['analytic_story']]:
                        return True

        elif yaml_key_name == "id":
            if yaml_data.get(yaml_key_name).lower() == field_name.lower():
                ColorPrint.print_success_fg(f"[+][SUCCESS]: ... found -> [ {yaml_data.get(yaml_key_name)} ]")
                return True

        return False
    
    def normalized_file_args(self, file_path:str)->list:
        """segregate string by possible Splunk Security content yaml field via regex"""
        ColorPrint.print_info_fg("[+][.  INFO]: ... segregating the file data ...")

        with open(file_path, "r") as f:
            lines = f.readlines()

        filter_line = [l.strip() for l in lines]
        
        segregate = defaultdict(list)
        regex_patterns = { 
            "detection_filename": r"^[a-z0-9_]+(?:\.yml)?$",
            "guid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            "mitre_attack_tid": r"^T\d{4}(?:\.\d{3})?$",
            "detection_and_analytic_story_name": r"^[A-Za-z0-9\s\-]+$"
            }
        
        
        for item in filter_line:
            found_category = False
            for category, pattern in regex_patterns.items():
                if re.fullmatch(pattern, item): # fullmatch ensures the entire string matches the pattern
                    segregate[category].append(item)

                    found_category = True
            
            if not found_category:
                
                ColorPrint.print_warning_fg(f"[!][WARNING]: ... {item} - No category matched.")
        

        ### remove guid and technique id catched by generic regex detection__and_analytic_story_name
        if 'detection_and_analytic_story_name' in segregate and ("guid" in segregate or "mitre_attack_tid" in segregate):
            removed_list = []
            for v in segregate['detection_and_analytic_story_name']:
                if v in segregate['guid']:
                    removed_list.append(v)
                if v in segregate['mitre_attack_tid']:
                    removed_list.append(v)
            for r in removed_list:
                segregate['detection_and_analytic_story_name'].remove(r)
        regular_dict = dict(segregate)
        beautified_json_string = json.dumps(regular_dict, indent=4)

        ### comment me if you dont want to see the replay_cache yml file
        if self.read_config_settings('debug_print'):
            ColorPrint.print_yellow_fg(Style.DIM + self.header_divider("STRING CATEGORIZATION"))
            ColorPrint.print_yellow_fg(Style.DIM + f"[+] ... \n{beautified_json_string}")
            ColorPrint.print_yellow_fg(Style.DIM + self.footer_divider("STRING CATEGORIZATION"))      
        return segregate
    
    def process_local_yaml_cache(self, local_replayed_yaml_dir_path:str,index_value:str)->None:
        """Process local YAML cache files for replaying attack data."""
        ### check which setup version of total-replay should be enable. attack range or attack data
        self.header_val  = ""
        self.header_val  = self.check_total_replay_setup()
        
        if not os.path.isdir(local_replayed_yaml_dir_path):
            ColorPrint.print_error_fg(f"[-][. ERROR]: ... Inputted {local_replayed_yaml_dir_path} is invalid!")
            return
        else:
            ctr = 1
            for root, dirs, files in os.walk(local_replayed_yaml_dir_path):
                for file in files:
                    ColorPrint.print_info_fg(f'[+][.  INFO]: ... Processing {ctr} => [ {file} ]')
                    file_path = os.path.join(root, file)

                    if file.endswith((".yaml",".yml")):
                        yaml_data = self.read_yaml_file(file_path)

                        if yaml_data is None:
                            ColorPrint.print_error_fg(f"[-][. ERROR]: ... Skipping empty or invalid YAML file: {file_path}")
                            continue
                        
                        ### comment me if you dont want to see the replay_cache yml file
                        if self.read_config_settings('debug_print'):
                            ColorPrint.print_yellow_fg(Style.DIM + self.header_divider("TOTAL-REPLAY CACHE YAML FILE", "local cache"))
                            ColorPrint.print_yellow_fg(Style.DIM + f"[+] ... \n{json.dumps(yaml_data, indent=4)}")
                            ColorPrint.print_yellow_fg(Style.DIM + self.footer_divider("TOTAL-REPLAY CACHE YAML FILE"))

                        ### simple logic to avoid replaying the same attack data again and again
                        if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON": 
                            if yaml_data['attack_data_uuid'] in self.processed_attack_data_uuid:
                                ColorPrint.print_info_fg(Style.BRIGHT + f"[+][.  INFO]: ... ATTACK_DATA UUID: {yaml_data['attack_data_uuid']} has already been replayed.")
                                ctr+=1
                                continue
                    
                            self.processed_attack_data_uuid.append(yaml_data['attack_data_uuid'])

                        if self.header_val == "TOTAL_REPLAY_ATTACK_DATA_ON":
                            self.attack_data_replay_cmd(yaml_data, index_value)
                        if self.header_val == "TOTAL_REPLAY_ATTACK_RANGE_ON":
                            self.attack_range_replay_cmd(yaml_data, index_value)
                        

                        ctr+=1
                        ColorPrint.print_magenta_fg("\n[+]" + "█" * 160 + "\n")


        return True
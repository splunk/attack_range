
from modules.IEnvironmentController import IEnvironmentController
from python_terraform import *
from modules import aws_service, splunk_sdk, github_service, azure_service
from tabulate import tabulate
import ansible_runner
import yaml
import time
import os
import glob
import sys
import re
import requests
import json
from shutil import copyfile
from datetime import datetime
from datetime import timedelta
import fileinput
import pyperclip



class TerraformController(IEnvironmentController):

    def __init__(self, config, log):
        super().__init__(config, log)
        statefile = self.config['range_name'] + ".terraform.tfstate"
        if self.config['cloud_provider'] == 'aws':
            self.config["statepath"] = os.path.join(os.path.dirname(__file__), '../terraform/aws/local/state', statefile)
        elif self.config['cloud_provider'] == 'azure':
            self.config["statepath"] = os.path.join(os.path.dirname(__file__), '../terraform/azure/local/state', statefile)

        self.config['splunk_es_app_version'] = re.findall(r'\d+', self.config['splunk_es_app'])[0]

        custom_dict = self.config.copy()
        variables = dict()
        variables['config'] = custom_dict

        if self.config['tf_backend'] == 'remote':
            with open(os.path.join(os.path.dirname(__file__), '../terraform', self.config['cloud_provider'], 'remote/resources.tf.j2'), 'r') as file :
                filedata = file.read()

            filedata = filedata.replace('[region]', self.config['region'])
            filedata = filedata.replace('[backend]', self.config['tf_backend_name'])
            filedata = filedata.replace('[tf_backend_ressource_group]', self.config['tf_backend_ressource_group'])
            filedata = filedata.replace('[tf_backend_storage_account]', self.config['tf_backend_storage_account'])
            filedata = filedata.replace('[tf_backend_container]', self.config['tf_backend_container'])

            with open(os.path.join(os.path.dirname(__file__), '../terraform', self.config['cloud_provider'], 'remote/resources.tf'), 'w+') as file:
                file.write(filedata)
        working_dir = os.path.join(os.path.dirname(__file__), '../terraform', self.config['cloud_provider'], self.config['tf_backend'])

        self.terraform = Terraform(working_dir=working_dir,variables=variables, parallelism=15 ,state=config["statepath"])


    def build(self):
        self.log.info("[action] > build\n")
        cwd = os.getcwd()
        os.system('cd ' + os.path.join(os.path.dirname(__file__), '../terraform', self.config['cloud_provider'], self.config['tf_backend']) + ' && terraform init ')
        os.system('cd ' + cwd)
        return_code, stdout, stderr = self.terraform.apply(
            capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        if not return_code:
            self.log.info(
                "attack_range has been built using terraform successfully")
            self.list_machines()

    def destroy(self):
        self.log.info("[action] > destroy\n")
        cwd = os.getcwd()
        os.system('cd ' + os.path.join(os.path.dirname(__file__), '../terraform', self.config['cloud_provider'], self.config['tf_backend']) + ' && terraform init ')
        os.system('cd ' + cwd)
        return_code, stdout, stderr = self.terraform.destroy(
            capture_output='yes', no_color=IsNotFlagged, force=IsNotFlagged, auto_approve=True)
        self.log.info("Destroyed with return code: " + str(return_code))
        statepath = self.config["statepath"]
        statebakpath = self.config["statepath"] + ".backup"
        if os.path.exists(statepath) and return_code==0:
            try:
                os.remove(statepath)
                os.remove(statebakpath)
            except Exception as e:
                self.log.error("not able to delete state file")
        self.log.info(
            "attack_range has been destroy using terraform successfully")

    def stop(self):
        if self.config['cloud_provider'] == 'aws':
            instances = aws_service.get_all_instances(self.config)
            aws_service.change_ec2_state(instances, 'stopped', self.log, self.config)
        elif self.config['cloud_provider'] == 'azure':
            azure_service.change_instance_state(self.config, 'stopped', self.log)

    def resume(self):
        if self.config['cloud_provider'] == 'aws':
            instances = aws_service.get_all_instances(self.config)
            aws_service.change_ec2_state(instances, 'running', self.log, self.config)
        elif self.config['cloud_provider'] == 'azure':
            azure_service.change_instance_state(self.config, 'running', self.log)

    def test(self, test_files, test_build_destroy, test_delete_data):

        if test_build_destroy:
            # build attack range
            self.build()

        result_tests = []
        for test_file in test_files:
            # read test file
            self.log.info("running test: {0}".format(test_file))
            test_file = self.load_file(test_file)

            if self.config['update_escu_app'] == '1':
                self.update_ESCU_app()

            for test in test_file['tests']:
                epoch_time = str(int(time.time()))
                dump_name = folder_name = "attack_data_" + epoch_time + "_" + test['name'].lower().replace(" ", "_").replace(".", "_")
                result_test = {}
                for attack_data in test['attack_data']:
                    if 'update_timestamp' in attack_data:
                        attack_data['update_timestamp'] = attack_data['update_timestamp']
                    else:
                        attack_data['update_timestamp'] = False
                    #attack_data['update_timestamp'] = True
                    attack_data['index'] = 'test'
                    self.replay_attack_data(dump_name, attack_data)

                # wait for indexing
                self.log.info("sleeping for 60 seconds to wait for indexing to occur")
                time.sleep(60)

                # process baselines
                if 'baselines' in test:
                    results_baselines = []
                    for baseline_obj in test['baselines']:
                        baseline_file_name = baseline_obj['file']
                        baseline = self.load_file(os.path.join(os.path.dirname(__file__), '../' + self.config['security_content_path'] + '/' + baseline_file_name))
                        result_obj = dict()
                        result_obj['baseline'] = baseline_obj['name']
                        result_obj['baseline_file'] = baseline_obj['file']
                        if self.config['cloud_provider'] == 'aws':
                            instance = aws_service.get_instance_by_name(
                                'ar-splunk-' + self.config['range_name'] + '-' + self.config['key_name'], self.config)
                            if instance['State']['Name'] == 'running':
                                result = splunk_sdk.test_baseline_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['attack_range_password']), baseline['search'], baseline_obj['pass_condition'], baseline['name'], baseline_obj['file'], baseline_obj['earliest_time'], baseline_obj['latest_time'], self.log)
                                results_baselines.append(result)
                            else:
                                self.log.error('ERROR: splunk server is not running.')
                        elif self.config['cloud_provider'] == 'azure':
                            instance = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)
                            if instance['vm_obj'].instance_view.statuses[1].display_status == "VM running":
                                result = splunk_sdk.test_baseline_search(instance['public_ip'], str(self.config['attack_range_password']), baseline['search'], baseline_obj['pass_condition'], baseline['name'], baseline_obj['file'], baseline_obj['earliest_time'], baseline_obj['latest_time'], self.log)
                                results_baselines.append(result)
                    result_test['baselines_result'] = results_baselines

                # validate detection works
                detection_file_name = test['file']
                detection = self.load_file(os.path.join(os.path.dirname(__file__), '../' + self.config['security_content_path'] + '/detections/' + detection_file_name))
                if self.config['cloud_provider'] == 'aws':
                    instance = aws_service.get_instance_by_name(
                        'ar-splunk-' + self.config['range_name'] + '-' + self.config['key_name'], self.config)
                    if instance['State']['Name'] == 'running':
                        self.log.info("running detection against splunk for indexed data {0}".format(detection_file_name))
                        result_detection = splunk_sdk.test_detection_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['attack_range_password']), detection['search'], test['pass_condition'], detection['name'], test['file'], test['earliest_time'], test['latest_time'], self.log)
                        if test_delete_data:
                            self.log.info("deleting test data from splunk for test {0}".format(detection_file_name))
                            splunk_sdk.delete_attack_data(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['attack_range_password']))
                    else:
                        self.log.error('ERROR: splunk server is not running.')

                elif self.config['cloud_provider'] == 'azure':
                    instance = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)
                    if instance['vm_obj'].instance_view.statuses[1].display_status == "VM running":
                        self.log.info("running detection against splunk for indexed data {0}".format(detection_file_name))
                        result_detection = splunk_sdk.test_detection_search(instance['public_ip'], str(self.config['attack_range_password']), detection['search'], test['pass_condition'], detection['name'], test['file'], test['earliest_time'], test['latest_time'], self.log)
                        if test_delete_data:
                            self.log.info("deleting test data from splunk for test {0}".format(detection_file_name))
                            splunk_sdk.delete_attack_data(instance['public_ip'], str(self.config['attack_range_password']))

                result_detection['detection_name'] = test['name']
                result_detection['detection_file'] = test['file']
                result_test['detection_result'] = result_detection
                result_tests.append(result_test)

        self.log.info('testing completed.')
        if test_build_destroy:
            # destroy attack range
            self.destroy()

        return result_tests


    def load_file(self, file_path):
        with open(file_path, 'r', encoding="utf-8") as stream:
            try:
                file = list(yaml.safe_load_all(stream))[0]
            except yaml.YAMLError as exc:
                self.log.error(exc)
                sys.exit("ERROR: reading {0}".format(file_path))
        return file


    def simulate(self, simulation_type, target, simulation_techniques, simulation_atomics, simulation_playbook, var_str='no'):
        if self.config['cloud_provider'] == 'aws':
            target_public_ip = aws_service.get_single_instance_public_ip(target, self.config)
            ansible_user = 'Administrator'
            ansible_port = 5986
        elif self.config['cloud_provider'] == 'azure':
            target_public_ip = azure_service.get_instance(self.config, target, self.log)['public_ip']
            ansible_user = 'AzureAdmin'
            ansible_port = 5985

        start_time = time.time()

        if simulation_type == 'ART':

            # check if specific atomics are used then it's not allowed to multiple techniques
            techniques_arr = simulation_techniques.split(',')
            if (len(techniques_arr) > 1) and (simulation_atomics != 'no'):
                self.log.error(
                    'ERROR: if simulation_atomics are used, only a single simulation_technique is allowed.')
                sys.exit(1)

            run_specific_atomic_tests = 'True'
            if simulation_atomics == 'no':
                run_specific_atomic_tests = 'False'

            if target == "ar-win-client-" + self.config['range_name'] + "-" + self.config['key_name']:
                runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                    cmdline=str('-i ' + target_public_ip + ', '),
                                    roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                    playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/atomic_red_team.yml'),
                                    extravars={'ansible_port': 5985, 'var_str': var_str, 'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': ansible_user, 'ansible_password': self.config['attack_range_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http', 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                                    verbosity=0)
            else:


                runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                cmdline=str('-i ' + target_public_ip + ', '),
                                roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/atomic_red_team.yml'),
                                extravars={'ansible_port': ansible_port, 'var_str': var_str, 'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': ansible_user, 'ansible_password': self.config['attack_range_password'], 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                                verbosity=0)

        
        elif simulation_type == 'PurpleSharp':

            copyfile(simulation_playbook, os.path.join(os.path.dirname(__file__), '../ansible/roles/purplesharp/files/simulation_playbook.json'))

            if target == "ar-win-client-" + self.config['range_name'] + "-" + self.config['key_name']:
                runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                cmdline=str('-i ' + target_public_ip + ', '),
                                roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/purplesharp.yml'),
                                extravars={'ansible_port': 5985, 'var_str': var_str, 'ansible_user': ansible_user, 'ansible_password': self.config['attack_range_password'] }, 
                                verbosity=0)
            else:
                runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                cmdline=str('-i ' + target_public_ip + ', '),
                                roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/purplesharp.yml'),
                                extravars={'ansible_port': ansible_port, 'var_str': var_str, 'ansible_user': ansible_user, 'ansible_password': self.config['attack_range_password']},
                                verbosity=0)



        if runner.status == "successful":
            output = []
            if 'output_art' in runner.get_fact_cache(target_public_ip):
                stdout_lines = runner.get_fact_cache(target_public_ip)['output_art']['stdout_lines']
            else:
                stdout_lines = runner.get_fact_cache(target_public_ip)['output_art_var']['stdout_lines']

            i = 0
            for line in stdout_lines:
                match = re.search(r'Executing test: (.*)', line)
                if match is not None:
                    #print(match.group(1))
                    if re.match(r'Done executing test', stdout_lines[i+1]):
                        msg = 'Return value unclear for test ' + match.group(1)
                        self.log.info(msg)
                        output.append(msg)
                    else:
                        msg = 'Successful Execution of test ' + match.group(1)
                        self.log.info(msg)
                        output.append(msg)
                i += 1

            with open(os.path.join(os.path.dirname(__file__),
                                   "../attack_data/.%s-last-sim.tmp" % self.config['range_name']),
                      'w') as last_sim:
                last_sim.write("%s" % start_time)
            return output
        else:
            self.log.error("failed to executed technique ID {0} against target: {1}".format(
                simulation_techniques, target))
            sys.exit(1)

    def getIP(self, response, machine_type):
        for machine in response:
            for x in machine:
                    if machine_type in x:
                        ip = machine[2]
                        return ip


    def show_message(self, response):
        print_messages = []

        # splunk server will always be built
        splunk_ip = self.getIP(response, 'splunk')
        msg = "\n\nAccess Splunk via:\n\tWeb > http://" + splunk_ip + ":8000\n\tSSH > ssh -i" + self.config['private_key_path'] \
        + " ubuntu@" + splunk_ip + "\n\tusername: admin \n\tpassword: " + self.config['attack_range_password']
        print_messages.append(msg)

        # windows domain controller
        if self.config['windows_domain_controller'] == 1:
            win_ip = self.getIP(response, 'win-dc')
            msg = "Access Windows Domain Controller via:\n\tRDP > rdp://" + win_ip + ":3389\n\tusername: Administrator \n\tpassword: " + self.config['attack_range_password']
            print_messages.append(msg)

        # windows domain controller
        if self.config['windows_server'] == 1:
            win_server = self.getIP(response, 'win-server')
            msg = "Access Windows Server via:\n\tRDP > rdp://" + win_server + ":3389\n\tusername: Administrator \n\tpassword: " + self.config['attack_range_password']
            print_messages.append(msg)

        # kali linux
        if self.config['kali_machine'] == 1:
            kali_ip = self.getIP(response, 'kali')
            msg = "Access Kali via:\n\tSSH > ssh -i" + self.config['private_key_path'] \
            + " ubuntu@" + kali_ip + "\n\tusername: kali \n\tpassword: " + self.config['attack_range_password']
            print_messages.append(msg)

        # osquery linux
        if self.config['osquery_machine'] == 1:
            osquerylnx_ip = self.getIP(response, 'osquerylnx')
            msg = "Access Osquery via:\n\tSSH > ssh -i" + self.config['private_key_path'] \
            + " ubuntu@" + osquerylnx_ip + "\n\tusername: kali \n\tpassword: " + self.config['attack_range_password']
            print_messages.append(msg)

        # phantom linux
        if self.config['phantom_server'] == 1:
            phantom_ip = self.getIP(response, 'phantom')
            msg = "Access Phantom via:\n\tWeb > https://" + phantom_ip + "\n\tSSH > ssh -i" + self.config['private_key_path'] \
            + " centos@" + phantom_ip + "\n\tusername: admin \n\tpassword: " + self.config['attack_range_password']
            print_messages.append(msg)

        return print_messages


    def list_machines(self):
        if self.config['cloud_provider'] == 'aws':
            instances = aws_service.get_all_instances(self.config)
            response = []
            instances_running = False
            for instance in instances:
                if instance['State']['Name'] == 'running':
                    instances_running = True
                    response.append([instance['Tags'][0]['Value'], instance['State']['Name'],
                                     instance['NetworkInterfaces'][0]['Association']['PublicIp']])
                else:
                    response.append([instance['Tags'][0]['Value'],
                                     instance['State']['Name']])

        elif self.config['cloud_provider'] == 'azure':
            instances = azure_service.get_all_instances(self.config)
            response = []
            instances_running = False
            for instance in instances:
                if instance['vm_obj'].instance_view.statuses[1].display_status == "VM running":
                    instances_running = True
                    response.append([instance['vm_obj'].name, instance['vm_obj'].instance_view.statuses[1].display_status, instance['public_ip']])
                else:
                    response.append([instance['vm_obj'].name, instance['vm_obj'].instance_view.statuses[1].display_status])

        print()
        print('Status Virtual Machines\n')
        if len(response) > 0:

            if instances_running:
                print(tabulate(response, headers=[
                      'Name', 'Status', 'IP Address']))
                messages_to_print = self.show_message(response)
                for msg in messages_to_print:
                    print(msg)
            else:
                print(tabulate(response, headers=['Name', 'Status']))
                messages_to_print = self.show_message(response)
                for msg in messages_to_print:
                    print(msg)

        else:
            print("ERROR: Can't find configured Attack Range Instances")

        # copy password into clipboard
        try:
            pyperclip.copy(self.config['attack_range_password'])
            print("* attack_range password has been copied to your clipboard")
        except Exception as e:
            self.log.error("not able to copy password to clipboard")
        print()


    def dump_attack_data(self, dump_name, dump_data):
        self.log.info("Dump log data")

        folder = "attack_data/" + dump_name
        if os.path.isdir(os.path.join(os.path.dirname(__file__), '../' + folder)):
            self.log.error("folder already. please specify another directory")
            sys.exit(1)
        else:
            os.mkdir(os.path.join(os.path.dirname(__file__), '../' + folder))

        server_str = ("ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'])
        if self.config['cloud_provider'] == 'aws':
            target_public_ip = aws_service.get_single_instance_public_ip(server_str, self.config)
            ansible_user = 'Administrator'
            ansible_port = 5986
        elif self.config['cloud_provider'] == 'azure':
            target_public_ip = azure_service.get_instance(self.config, server_str, self.log)['public_ip']
            ansible_user = 'AzureAdmin'
            ansible_port = 5985


        dump_search = "search %s earliest=-%s latest=%s | sort 0 _time" \
            % (dump_data['search'], dump_data['earliest'], dump_data['latest'])
        dump_info = "Dumping Splunk Search to %s " % dump_data['out']
        self.log.info(dump_info)
        out = open(os.path.join(os.path.dirname(__file__), "../attack_data/" + dump_name + "/" + dump_data['out']), 'wb')
        splunk_sdk.export_search(target_public_ip,
                                    s=dump_search,
                                    password=self.config['attack_range_password'],
                                    out=out)
        out.close()
        self.log.info("%s [Completed]" % dump_info)


    def replay_attack_data(self, dump_name, attack_data):
        if self.config['cloud_provider'] == 'aws':
            splunk_ip = aws_service.get_single_instance_public_ip("ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.config)
        elif self.config['cloud_provider'] == 'azure':
            splunk_ip = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)['public_ip']

        # preset our ansible vars
        ansible_vars = {}
        ansible_vars['dump_name'] = dump_name
        ansible_vars['ansible_user'] = 'ubuntu'
        ansible_vars['ansible_ssh_private_key_file'] = self.config['private_key_path']
        ansible_vars['splunk_password'] = self.config['attack_range_password']
        ansible_vars['ansible_port'] = 22

        ansible_vars['out'] = attack_data['file_name']
        ansible_vars['sourcetype'] = attack_data['sourcetype']
        ansible_vars['source'] = attack_data['source']
        ansible_vars['index'] = attack_data['index']
        ansible_vars['update_timestamp'] = attack_data['update_timestamp']

        if 'data' in attack_data:
            ansible_vars['data'] = attack_data['data']
            ansible_vars['local_data'] = False
        else:
            ansible_vars['local_data'] = True

        # call ansible
        cmdline = "-i %s, -u ubuntu" % (splunk_ip)
        runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                    cmdline=cmdline,
                                    roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                    playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/attack_test.yml'),
                                    extravars=ansible_vars,)


    def update_ESCU_app(self):
        self.log.info("Update ESCU App. This can take some time")
        # upload package
        if self.config['cloud_provider'] == 'aws':
            splunk_ip = aws_service.get_single_instance_public_ip('ar-splunk-' + self.config['range_name'] + '-' + self.config['key_name'], self.config)
        elif self.config['cloud_provider'] == 'azure':
            splunk_ip = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)['public_ip']
        # Upload the replay logs to the Splunk server
        ansible_vars = {}
        ansible_vars['ansible_user'] = 'ubuntu'
        ansible_vars['ansible_ssh_private_key_file'] = self.config['private_key_path']
        ansible_vars['splunk_password'] = self.config['attack_range_password']
        ansible_vars['security_content_path'] = self.config['security_content_path']

        cmdline = "-i %s, -u ubuntu" % (splunk_ip)
        runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                    cmdline=cmdline,
                                    roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                    playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/update_escu.yml'),
                                    extravars=ansible_vars)


    def execute_savedsearch(self, search_name, earliest, latest):
        self.log.info("Execute savedsearch " + search_name)

        if self.config['cloud_provider'] == 'aws':
            splunk_ip = aws_service.get_single_instance_public_ip("ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.config)
        elif self.config['cloud_provider'] == 'azure':
            splunk_ip = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)['public_ip']

        splunk_sdk.execute_savedsearch(splunk_ip, self.config['attack_range_password'], search_name, earliest, latest)

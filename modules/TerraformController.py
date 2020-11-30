
from modules.IEnvironmentController import IEnvironmentController
from python_terraform import *
from modules import aws_service, splunk_sdk, github_service, azure_service
from modules.DataManipulation import DataManipulation
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
from datetime import datetime
from datetime import timedelta
import fileinput



class TerraformController(IEnvironmentController):

    def __init__(self, config, log):
        super().__init__(config, log)
        statefile = self.config['range_name'] + ".terraform.tfstate"
        if self.config['cloud_provider'] == 'aws':
            self.config["statepath"] = os.path.join(os.path.dirname(__file__), '../terraform/aws/state', statefile)
        elif self.config['cloud_provider'] == 'azure':
            self.config["statepath"] = os.path.join(os.path.dirname(__file__), '../terraform/azure/state', statefile)
        custom_dict = self.config.copy()
        variables = dict()
        variables['config'] = custom_dict
        if self.config['cloud_provider'] == 'aws':
            self.terraform = Terraform(working_dir=os.path.join(os.path.dirname(__file__), '../terraform/aws'),variables=variables, parallelism=15 ,state=config["statepath"])
        elif self.config['cloud_provider'] == 'azure':
            self.terraform = Terraform(working_dir=os.path.join(os.path.dirname(__file__), '../terraform/azure'),variables=variables, parallelism=15 ,state=config["statepath"])


    def build(self):
        self.log.info("[action] > build\n")
        return_code, stdout, stderr = self.terraform.apply(
            capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        if not return_code:
            self.log.info(
                "attack_range has been built using terraform successfully")
            self.list_machines()

    def destroy(self):
        self.log.info("[action] > destroy\n")
        return_code, stdout, stderr = self.terraform.destroy(
            capture_output='yes', no_color=IsNotFlagged)
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

    def test(self, test_file):
        # read test file
        test_file = self.load_file(test_file)

        # build attack range
        self.build()

        epoch_time = str(int(time.time()))
        folder_name = "attack_data_" + epoch_time
        os.mkdir(os.path.join(os.path.dirname(__file__), '../attack_data/' + folder_name))

        output = 'loaded attack data'

        if self.config['update_escu_app'] == '1':
            self.update_ESCU_app()

        result_tests = []

        for test in test_file['tests']:
            result_test = {}
            for attack_data in test['attack_data']:
                url = attack_data['data']
                r = requests.get(url, allow_redirects=True)
                open(os.path.join(os.path.dirname(__file__), '../attack_data/' + folder_name + '/' + attack_data['file_name']), 'wb').write(r.content)

                # Update timestamps before replay
                if 'update_timestamp' in attack_data:
                    if attack_data['update_timestamp'] == True:
                        data_manipulation = DataManipulation()
                        data_manipulation.manipulate_timestamp(folder_name + '/' + attack_data['file_name'], self.log, attack_data['sourcetype'], attack_data['source'])

                self.replay_attack_data(folder_name, None, {'sourcetype': attack_data['sourcetype'], 'source': attack_data['source'], 'out': attack_data['file_name']})

            self.log.info('Wait for 200 seconds')
            time.sleep(200)

            if 'baselines' in test:
                results_baselines = []
                for baseline_obj in test['baselines']:
                    baseline_file_name = baseline_obj['file']
                    baseline = self.load_file(os.path.join(os.path.dirname(__file__), '../../security-content/' + baseline_file_name))
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
                            self.log.error('ERROR: Splunk server is not running.')
                    elif self.config['cloud_provider'] == 'azure':
                        instance = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)
                        if instance['vm_obj'].instance_view.statuses[1].display_status == "VM running":
                            result = splunk_sdk.test_baseline_search(instance['public_ip'], str(self.config['attack_range_password']), baseline['search'], baseline_obj['pass_condition'], baseline['name'], baseline_obj['file'], baseline_obj['earliest_time'], baseline_obj['latest_time'], self.log)
                            results_baselines.append(result)
                result_test['baselines_result'] = results_baselines

            detection_file_name = test['file']
            detection = self.load_file(os.path.join(os.path.dirname(__file__), '../../security-content/detections/' + detection_file_name))
            if self.config['cloud_provider'] == 'aws':
                instance = aws_service.get_instance_by_name(
                    'ar-splunk-' + self.config['range_name'] + '-' + self.config['key_name'], self.config)
                if instance['State']['Name'] == 'running':
                    result_detection = splunk_sdk.test_detection_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['attack_range_password']), detection['search'], test['pass_condition'], detection['name'], test['file'], test['earliest_time'], test['latest_time'], self.log)
                    self.log.info('Running Detections now.')
                else:
                    self.log.error('ERROR: Splunk server is not running.')
            elif self.config['cloud_provider'] == 'azure':
                instance = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)
                if instance['vm_obj'].instance_view.statuses[1].display_status == "VM running":
                    result_detection = splunk_sdk.test_detection_search(instance['public_ip'], str(self.config['attack_range_password']), detection['search'], test['pass_condition'], detection['name'], test['file'], test['earliest_time'], test['latest_time'], self.log)
                    self.log.info('Running Detections now.')

            result_detection['detection_name'] = test['name']
            result_detection['detection_file'] = test['file']
            result_test['detection_result'] = result_detection
            result_tests.append(result_test)

        self.log.info('Running Detections - Complete')

        # destroy attack range
        self.destroy()

        return result_tests


    def load_file(self, file_path):
        with open(file_path, 'r') as stream:
            try:
                file = list(yaml.safe_load_all(stream))[0]
            except yaml.YAMLError as exc:
                self.log.error(exc)
                sys.exit("ERROR: reading {0}".format(file_path))
        return file


    def simulate(self, target, simulation_techniques, simulation_atomics, var_str='no'):
        if self.config['cloud_provider'] == 'aws':
            target_public_ip = aws_service.get_single_instance_public_ip(target, self.config)
            ansible_user = 'Administrator'
            ansible_port = 5986
        elif self.config['cloud_provider'] == 'azure':
            target_public_ip = azure_service.get_instance(self.config, target, self.log)['public_ip']
            ansible_user = 'AzureAdmin'
            ansible_port = 5985

        start_time = time.time()

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
            else:
                print(tabulate(response, headers=['Name', 'Status']))
        else:
            print("ERROR: Can't find configured Attack Range Instances")
        print()


    def dump_attack_data(self, dump_name, last_sim):
        self.log.info("Dump log data")

        folder = "attack_data/" + dump_name
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

        with open(os.path.join(os.path.dirname(__file__), '../attack_data/dumps.yml')) as dumps:
            for dump in yaml.full_load(dumps):
                if dump['enabled']:
                    dump_out = dump['dump_parameters']['out']
                    if last_sim:
                        # if last_sim is set, then it overrides time in dumps.yml
                        # and starts dumping from last simulation
                        with open(os.path.join(os.path.dirname(__file__),
                                               "../attack_data/.%s-last-sim.tmp" % self.config['range_name']),
                                  'r') as ls:
                            sim_ts = float(ls.readline())
                            dump['dump_parameters']['time'] = "-%ds" % int(time.time() - sim_ts)
                    dump_search = "search %s earliest=%s | sort 0 _time" \
                                  % (dump['dump_parameters']['search'], dump['dump_parameters']['time'])
                    dump_info = "Dumping Splunk Search to %s " % dump_out
                    self.log.info(dump_info)
                    out = open(os.path.join(os.path.dirname(__file__), "../attack_data/" + dump_name + "/" + dump_out), 'wb')
                    splunk_sdk.export_search(target_public_ip,
                                             s=dump_search,
                                             password=self.config['attack_range_password'],
                                             out=out)
                    out.close()
                    self.log.info("%s [Completed]" % dump_info)


    def replay_attack_data(self, dump_name, dump, replay_parameters = None):
        if self.config['cloud_provider'] == 'aws':
            splunk_ip = aws_service.get_single_instance_public_ip("ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.config)
        elif self.config['cloud_provider'] == 'azure':
            splunk_ip = azure_service.get_instance(self.config, "ar-splunk-" + self.config['range_name'] + "-" + self.config['key_name'], self.log)['public_ip']

        if replay_parameters == None:
            with open(os.path.join(os.path.dirname(__file__), '../attack_data/dumps.yml')) as dump_fh:
                for d in yaml.full_load(dump_fh):
                    if (d['name'] == dump or dump is None) and d['enabled']:
                        self.replay_attack_dataset(splunk_ip, dump_name, d['replay_parameters']['index'], d['replay_parameters']['sourcetype'], d['replay_parameters']['source'], d['dump_parameters']['out'])
        else:
            self.replay_attack_dataset(splunk_ip, dump_name, 'test', replay_parameters['sourcetype'], replay_parameters['source'], replay_parameters['out'])


    def replay_attack_dataset(self, splunk_ip, dump_name, index, sourcetype, source, out):
        ansible_vars = {}
        ansible_vars['dump_name'] = dump_name
        ansible_vars['ansible_user'] = 'ubuntu'
        ansible_vars['ansible_ssh_private_key_file'] = self.config['private_key_path']
        ansible_vars['splunk_password'] = self.config['attack_range_password']
        ansible_vars['out'] = out
        ansible_vars['sourcetype'] = sourcetype
        ansible_vars['source'] = source
        ansible_vars['index'] = index

        cmdline = "-i %s, -u ubuntu" % (splunk_ip)
        runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../'),
                                    cmdline=cmdline,
                                    roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                    playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/attack_replay.yml'),
                                    extravars=ansible_vars)

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

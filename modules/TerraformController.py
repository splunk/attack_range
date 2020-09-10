
from modules.IEnvironmentController import IEnvironmentController
from python_terraform import *
from modules import aws_service, splunk_sdk, github_service
from tabulate import tabulate
import ansible_runner
import yaml
import time
import os
import glob
import sys


class TerraformController(IEnvironmentController):

    def __init__(self, config, log):
        super().__init__(config, log)
        statefile = self.config['range_name'] + ".terraform.tfstate"
        config["statepath"] = os.path.join('state', statefile)
        custom_dict = self.config.copy()
        variables = dict()
        variables['config'] = custom_dict
        self.terraform = Terraform(working_dir=os.path.join(os.path.dirname(__file__), '../terraform'),variables=variables, parallelism=15 ,state=config["statepath"])


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
        statepath = "terraform/" + self.config["statepath"]
        statebakpath = "terraform/" + self.config["statepath"] + ".backup"
        if os.path.exists(statepath) and return_code==0:
            os.remove(statepath)
            os.remove(statebakpath)
        self.log.info(
            "attack_range has been destroy using terraform successfully")

    def stop(self):
        instances = aws_service.get_all_instances(self.config)
        aws_service.change_ec2_state(instances, 'stopped', self.log, self.config)

    def resume(self):
        instances = aws_service.get_all_instances(self.config)
        aws_service.change_ec2_state(instances, 'running', self.log, self.config)

    def test(self, test_file):
        # read test file
        test_file = self.load_file(test_file)

        # build attack range
        self.build()

        # wait
        self.log.info('Wait for 200 seconds before running simulations.')
        time.sleep(200)

        # simulate attack
        # create vars string for custom vars:
        if 'vars' in test_file:
            var_str = '$myArgs = @{ '
            i = 0
            for key, value in test_file['vars'].items():
                if i == 0:
                    var_str += '"' + key + '" = "' + value + '"'
                    i += 1
                else:
                    var_str += '; "' + key + '" = "' + value + '"'
                    i += 1

            var_str += ' }'
            print(var_str)

            self.simulate(
                test_file['target'], test_file['simulation_technique'], 'no', var_str)

        else:
            self.simulate(test_file['target'],
                          test_file['simulation_technique'], 'no')

        # wait
        self.log.info('Wait for 200 seconds before running the detections.')
        time.sleep(200)

        # run detection
        result = []

        for detection_obj in test_file['detections']:
            detection_file_name = detection_obj['name'].replace('-','_').replace(' ','_').lower() + '.yml'
            detection = self.load_file(os.path.join(os.path.dirname(__file__), '../../security-content/detections/' + detection_file_name))
            result_obj = dict()
            result_obj['detection'] = detection_obj['name']
            instance = aws_service.get_instance_by_name(
                self.config['range_name'] + "-attack-range-splunk-server", self.config)
            if instance['State']['Name'] == 'running':
                result_obj['error'], result_obj['results'] = splunk_sdk.test_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['attack_range_password']), detection['search'], detection_obj['pass_condition'], detection['name'], self.log)
            else:
                self.log.error('ERROR: Splunk server is not running.')
            result.append(result_obj)

        # print(result)

        # store attack data
        if self.config['capture_attack_data'] == '1':
            self.dump_attack_data(test_file['simulation_technique'])

        # destroy attack range
        self.destroy()

        # return results
        return {'technique': test_file['simulation_technique'], 'results': result }

    def load_file(self, file_path):
        with open(file_path, 'r') as stream:
            try:
                file = list(yaml.safe_load_all(stream))[0]
            except yaml.YAMLError as exc:
                self.log.error(exc)
                sys.exit("ERROR: reading {0}".format(file_path))
        return file

    def simulate(self, target, simulation_techniques, simulation_atomics, var_str='no'):
        target_public_ip = aws_service.get_single_instance_public_ip(
            target, self.config)

        # check if specific atomics are used then it's not allowed to multiple techniques
        techniques_arr = simulation_techniques.split(',')
        if (len(techniques_arr) > 1) and (simulation_atomics != 'no'):
            self.log.error(
                'ERROR: if simulation_atomics are used, only a single simulation_technique is allowed.')
            sys.exit(1)

        run_specific_atomic_tests = 'True'
        if simulation_atomics == 'no':
            run_specific_atomic_tests = 'False'

        if target == 'attack-range-windows-client':
            runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../../attack_range/'),
                                   cmdline=str('-i ' + target_public_ip + ', '),
                                   roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                   playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/atomic_red_team.yml'),
                                   extravars={'var_str': var_str, 'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http', 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                                   verbosity=0)
        else:
            runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../../attack_range/'),
                               cmdline=str('-i ' + target_public_ip + ', '),
                               roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                               playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/atomic_red_team.yml'),
                               extravars={'var_str': var_str, 'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                               verbosity=0)

        if runner.status == "successful":
            self.log.info("successfully executed technique ID {0} against target: {1}".format(
                simulation_techniques, target))
        else:
            self.log.error("failed to executed technique ID {0} against target: {1}".format(
                simulation_techniques, target))
            sys.exit(1)

    def list_machines(self):
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
        print()
        print('Status EC2 Machines\n')
        if len(response) > 0:
            if instances_running:
                print(tabulate(response, headers=[
                      'Name', 'Status', 'IP Address']))
            else:
                print(tabulate(response, headers=['Name', 'Status']))
        else:
            print("ERROR: Can't find configured EC2 Attack Range Instances in AWS.")
        print()

    def dump_attack_data(self, dump_name):

        # copy json from nxlog
        # copy raw data using powershell
        # copy indexes
        # packet capture with netsh
        # see https://medium.com/threat-hunters-forge/mordor-pcaps-part-1-capturing-network-packets-from-windows-endpoints-with-network-shell-e117b84ec971

        self.log.info("Dump log data")

        folder = "attack_data/" + dump_name
        os.mkdir(os.path.join(os.path.dirname(__file__), '../' + folder))

        servers = ['splunk_server']
        if self.config['windows_domain_controller'] == '1':
            servers.append('windows-domain-controller')
        if self.config['windows_server'] == '1':
            servers.append('windows-server')

        # dump json and windows event logs from Windows servers
        for server in servers:
            server_str = (self.config['range_name'] + "-attack-range-" + server).replace("_", "-")
            target_public_ip = aws_service.get_single_instance_public_ip(server_str, self.config)

            if server_str == str(self.config['range_name'] +'-attack-range-windows-client'):
                runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../../attack_range/'),
                                       cmdline=str('-i ' + target_public_ip + ', '),
                                       roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                       playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/attack_data.yml'),
                                       extravars={'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http', 'hostname': server_str, 'folder': dump_name},
                                       verbosity=0)
            elif server_str == str(self.config['range_name'] + '-attack-range-splunk-server'):
                with open('attack_data/dumps.yml') as dumps:
                    for dump in yaml.full_load(dumps):
                        if dump['enabled']:
                            dump_out = dump['out']
                            dump_search = "search %s earliest=%s" % (dump['search'], dump['time'])
                            dump_info = "Dumping Splunk Search to %s " % dump_out
                            self.log.info(dump_info)
                            out = open("attack_data/%s/%s" % (dump_name, dump_out), 'w')
                            splunk_sdk.export_search(target_public_ip,
                                                     s=dump_search,
                                                     password=self.config['attack_range_password'],
                                                     out=out)
                            out.close()
                            self.log.info("%s [Completed]" % dump_info)
            else:
                runner = ansible_runner.run(private_data_dir=os.path.join(os.path.dirname(__file__), '../../attack_range/'),
                                       cmdline=str('-i ' + target_public_ip + ', '),
                                       roles_path=os.path.join(os.path.dirname(__file__), '../ansible/roles'),
                                       playbook=os.path.join(os.path.dirname(__file__), '../ansible/playbooks/attack_data.yml'),
                                       extravars={'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'hostname': server_str, 'folder': dump_name},
                                       verbosity=0)


        if self.config['sync_to_s3_bucket'] == '1':
            for file in glob.glob(os.path.join(os.path.dirname(__file__), '../' + folder + '/*')):
                self.log.info("upload attack data to S3 bucket. This can take some time")
                aws_service.upload_file_s3_bucket(self.config['s3_bucket_attack_data'], file, str(dump_name + '/' + os.path.basename(file)), self.config)


    def replay_attack_data(self, dump_name, dump):
        with open('attack_data/dumps.yml') as dump_fh:
            for d in yaml.full_load(dump_fh):
                if (d['name'] == dump or dump is None) and d['enabled']:
                    splunk_ip = aws_service.get_single_instance_public_ip("attack-range-splunk-server", self.config)
                    # Upload the replay logs to the Splunk server
                    d['dump_name'] = dump_name
                    d['ansible_user'] = 'ubuntu'
                    d['ansible_ssh_private_key_file'] = self.config['private_key_path']
                    d['splunk_password'] = self.config['attack_range_password']
                    cmdline = "-i %s, -u ubuntu -c paramiko" % (splunk_ip)
                    runner = ansible_runner.run(private_data_dir='.attack_range/',
                                                cmdline=cmdline,
                                                roles_path="../ansible/roles",
                                                playbook="../ansible/playbooks/attack_replay.yml",
                                                extravars=d)

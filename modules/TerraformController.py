
from modules.IEnvironmentController import IEnvironmentController
from python_terraform import *
from modules import aws_service, splunk_sdk, github_service
from tabulate import tabulate
import ansible_runner
import yaml
import time
import os
import glob


class TerraformController(IEnvironmentController):

    def __init__(self, config, log):
        super().__init__(config, log)
        custom_dict = self.config.copy()
        variables = dict()
        variables['config'] = custom_dict
        self.terraform = Terraform(working_dir='terraform',variables=variables)


    def build(self):
        self.log.info("[action] > build\n")
        return_code, stdout, stderr = self.terraform.apply(capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        if not return_code:
           self.log.info("attack_range has been built using terraform successfully")
           self.list_machines()


    def destroy(self):
        self.log.info("[action] > destroy\n")
        return_code, stdout, stderr = self.terraform.destroy(capture_output='yes', no_color=IsNotFlagged)
        self.log.info("attack_range has been destroy using terraform successfully")


    def stop(self):
        instances = aws_service.get_all_instances(self.config)
        aws_service.change_ec2_state(instances, 'stopped', self.log)


    def resume(self):
        instances = aws_service.get_all_instances(self.config)
        aws_service.change_ec2_state(instances, 'running', self.log)


    def test(self, test_file):
        # read test file
        test_file = self.load_file(test_file)

        # build attack range
        self.build()

        # wait
        self.log.info('Wait for 300 seconds before running simulations.')
        time.sleep(300)

        # simulate attack
        # create vars string for custom vars:
        if 'vars' in test_file:
            var_str = '$myArgs = @{ '
            i = 0
            for key, value in test_file['vars'].items():
                if i==0:
                    var_str += '"' + key + '" = "' + value + '"'
                    i += 1
                else:
                    var_str += '; "' + key + '" = "' + value + '"'
                    i += 1

            var_str += ' }'
            print(var_str)

            self.simulate(test_file['target'], test_file['simulation_technique'], 'no', var_str)

        else:
            self.simulate(test_file['target'], test_file['simulation_technique'], 'no')

        # wait
        self.log.info('Wait for 500 seconds before running the detections.')
        time.sleep(500)

        # run detection
        result = []

        for detection_obj in test_file['detections']:
            detection_file_name = detection_obj['name'].replace('-','_').replace(' ','_').lower() + '.yml'
            detection = self.load_file('../security-content/detections/' + detection_file_name)
            result_obj = dict()
            result_obj['detection'] = detection_obj['name']
            instance = aws_service.get_instance_by_name("attack-range-splunk-server",self.config)
            if instance['State']['Name'] == 'running':
                result_obj['error'], result_obj['results'] = splunk_sdk.test_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['attack_range_password']), detection['search'], detection_obj['pass_condition'], detection['name'], self.log)
            else:
                self.log.error('ERROR: Splunk server is not running.')
            result.append(result_obj)

        #print(result)

        # store attack data
        if self.config['capture_attack_data'] == '1':
            self.dump_attack_data(test_file['simulation_technique'])

        # destroy attack range
        self.destroy()

        #result_cond = False
        for result_obj in result:
            if result_obj['error']:
                self.log.error('Detection Testing failed: ' + result_obj['results']['detection_name'])
                if self.config['automated_testing'] == '1':
                    github_service.create_issue(result_obj['results']['detection_name'], self.config)
            #result_cond |= result_obj['error']
        sys.exit(0)


    def load_file(self, file_path):
        with open(file_path, 'r') as stream:
            try:
                file = list(yaml.safe_load_all(stream))[0]
            except yaml.YAMLError as exc:
                self.log.error(exc)
                sys.exit("ERROR: reading {0}".format(file_path))
        return file



    def simulate(self, target, simulation_techniques, simulation_atomics, var_str = 'no'):
        target_public_ip = aws_service.get_single_instance_public_ip(target, self.config)

        # check if specific atomics are used then it's not allowed to multiple techniques
        techniques_arr = simulation_techniques.split(',')
        if (len(techniques_arr) > 1) and (simulation_atomics != 'no'):
            self.log.error('ERROR: if simulation_atomics are used, only a single simulation_technique is allowed.')
            sys.exit(1)

        run_specific_atomic_tests = 'True'
        if simulation_atomics == 'no':
            run_specific_atomic_tests = 'False'

        if target == 'attack-range-windows-client':
            runner = ansible_runner.run(private_data_dir='.attack_range/',
                                   cmdline=str('-i ' + target_public_ip + ', '),
                                   roles_path="../ansible/roles",
                                   playbook='../ansible/playbooks/atomic_red_team.yml',
                                   extravars={'var_str': var_str, 'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http', 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                                   verbosity=0)
        else:
            runner = ansible_runner.run(private_data_dir='.attack_range/',
                               cmdline=str('-i ' + target_public_ip + ', '),
                               roles_path="../ansible/roles",
                               playbook='../ansible/playbooks/atomic_red_team.yml',
                               extravars={'var_str': var_str, 'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                               verbosity=0)

        if runner.status == "successful":
            self.log.info("successfully executed technique ID {0} against target: {1}".format(simulation_techniques, target))
        else:
            self.log.error("failed to executed technique ID {0} against target: {1}".format(simulation_techniques, target))
            sys.exit(1)


    def list_machines(self):
        instances = aws_service.get_all_instances(self.config)
        response = []
        instances_running = False
        for instance in instances:
            if instance['State']['Name'] == 'running':
                instances_running = True
                response.append([instance['Tags'][0]['Value'], instance['State']['Name'], instance['NetworkInterfaces'][0]['Association']['PublicIp']])
            else:
                response.append([instance['Tags'][0]['Value'], instance['State']['Name']])
        print()
        print('Status EC2 Machines\n')
        if len(response) > 0:
            if instances_running:
                print(tabulate(response, headers=['Name','Status', 'IP Address']))
            else:
                print(tabulate(response, headers=['Name','Status']))
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
        os.mkdir(folder)

        dump_searches = [
            {'dump': "attack_data/"+dump_name+"/windows-sec-events.out",
             'search':'search source=WinEventLog:Security New_Process_Name!="C:\\Program Files\\SplunkUniversalForwarder\\bin\\*"',
             'info': "Extracting Windows Event Logs from Splunk Server"},
        ]

        servers = ['splunk_server']
        if self.config['windows_domain_controller'] == '1':
            servers.append('windows_domain_controller')
        if self.config['windows_server'] == '1':
            servers.append('windows_server')

        # dump json and windows event logs from Windows servers
        for server in servers:
            server_str = ("attack-range-" + server).replace("_","-")
            target_public_ip = aws_service.get_single_instance_public_ip(server_str, self.config)

            if server_str == 'attack-range-windows-client':
                runner = ansible_runner.run(private_data_dir='.attack_range/',
                                       cmdline=str('-i ' + target_public_ip + ', '),
                                       roles_path="../ansible/roles",
                                       playbook='../ansible/playbooks/attack_data.yml',
                                       extravars={'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http', 'hostname': server_str, 'folder': dump_name},
                                       verbosity=0)
            elif server_str == 'attack-range-splunk-server':
                for dump in dump_searches:
                    self.log.info(dump['info'])
                    out = open(dump['dump'], 'w')
                    splunk_sdk.export_search(target_public_ip,
                                             s=dump['search'],
                                             password=self.config['attack_range_password'],
                                             out=out)
                    out.close()
                    self.log.info("%s [Completed]" % dump['info'])
            else:
                runner = ansible_runner.run(private_data_dir='.attack_range/',
                                       cmdline=str('-i ' + target_public_ip + ', '),
                                       roles_path="../ansible/roles",
                                       playbook='../ansible/playbooks/attack_data.yml',
                                       extravars={'ansible_user': 'Administrator', 'ansible_password': self.config['attack_range_password'], 'hostname': server_str, 'folder': dump_name},
                                       verbosity=0)

        if self.config['sync_to_s3_bucket'] == '1':
            for file in glob.glob(folder + "/*"):
                self.log.info("upload attack data to S3 bucket. This can take some time")
                aws_service.upload_file_s3_bucket(self.config['s3_bucket_attack_data'], file, str(dump_name + '/' + os.path.basename(file)))

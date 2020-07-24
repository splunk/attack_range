
from modules.IEnvironmentController import IEnvironmentController
from python_terraform import *
from modules import aws_service, splunk_sdk, kubernetes_service, github_service
from tabulate import tabulate
import ansible_runner
import yaml
import time
import tarfile
import os


class TerraformController(IEnvironmentController):

    def __init__(self, config, log, packer_amis):
        super().__init__(config, log)
        custom_dict = self.config.copy()
        rem_list = ['log_path', 'log_level', 'art_run_techniques', 'art_repository', 'art_branch', 'app', 'repo_name', 'repo_url', 'automated_testing', 'github_repo', 'github_token']
        [custom_dict.pop(key) for key in rem_list]
        custom_dict['ip_whitelist'] = [custom_dict['ip_whitelist']]
        if packer_amis:
            custom_dict['use_packer_amis'] = '1'
        else:
            custom_dict['use_packer_amis'] = '0'
        custom_dict['splunk_packer_ami'] = "packer-splunk-server-" + self.config['key_name']
        custom_dict['phantom_packer_ami'] = "packer-phantom-server-" + self.config['key_name']
        custom_dict['kali_machine_packer_ami'] = "packer-kali-machine-" + self.config['key_name']
        custom_dict['windows_domain_controller_packer_ami'] = "packer-windows-domain-controller-" + self.config['key_name']
        custom_dict['windows_server_packer_ami'] = "packer-windows-server-" + self.config['key_name']
        custom_dict['windows_client_packer_ami'] = "packer-windows-client-" + self.config['key_name']
        self.terraform = Terraform(working_dir='terraform',variables=custom_dict)


    def build(self):
        self.log.info("[action] > build\n")
        return_code, stdout, stderr = self.terraform.apply(capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        if not return_code:
           self.log.info("attack_range has been built using terraform successfully")
        if self.config["cloud_attack_range"]=="1":
            aws_service.provision_db(self.config, self.log)
        if self.config["kubernetes"]=="1":
            kubernetes_service.install_application(self.config, self.log)
        self.list_machines()


    def destroy(self):
        if self.config["kubernetes"]=="1":
            kubernetes_service.delete_application(self.config, self.log)
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

        # simulate attack
        self.simulate(test_file['target'], test_file['simulation_technique'])

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
                result_obj['error'], result_obj['results'] = splunk_sdk.test_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['splunk_admin_password']), detection['search'], detection_obj['pass_condition'], detection['name'], self.log)
            else:
                self.log.error('ERROR: Splunk server is not running.')
            result.append(result_obj)

        #print(result)

        # store attack data
        if self.config['capture_attack_data'] == '1':
            self.store_attack_data(result, test_file)

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


    def store_attack_data(self, results, test_file):
        target_public_ip = aws_service.get_single_instance_public_ip(test_file['target'], self.config)
        if test_file['target'] == 'attack-range-windows-client':
            runner = ansible_runner.run(private_data_dir='.attack_range/',
                                   cmdline=str('-i ' + target_public_ip + ', '),
                                   roles_path="../ansible/roles",
                                   playbook='../ansible/playbooks/attack_data.yml',
                                   extravars={'ansible_user': 'Administrator', 'ansible_password': self.config['win_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http'},
                                   verbosity=0)
        else:
            runner = ansible_runner.run(private_data_dir='.attack_range/',
                               cmdline=str('-i ' + target_public_ip + ', '),
                               roles_path="../ansible/roles",
                               playbook='../ansible/playbooks/attack_data.yml',
                               extravars={'ansible_user': 'Administrator', 'ansible_password': self.config['win_password']},
                               verbosity=0)

        aws_service.upload_file_s3_bucket('tmp/attack_data.txt', results, test_file, False)

        with tarfile.open('tmp/attack_data.tar.gz', "w:gz") as tar:
            tar.add('tmp/attack_data.txt', arcname="attack_data.txt")

        aws_service.upload_file_s3_bucket('tmp/attack_data.tar.gz', results, test_file, True)

        if os.path.exists('tmp/attack_data.tar.gz'):
            os.remove('tmp/attack_data.tar.gz')

        if os.path.exists('tmp/attack_data.txt'):
            os.remove('tmp/attack_data.txt')

        if runner.status == "successful":
            self.log.info("successfully stored attack data in S3 bucket")
        else:
            self.log.info("failed to store attack data in S3 bucket")


    def simulate(self, target, simulation_techniques, simulation_atomics):
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
                                   extravars={'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['win_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http', 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                                   verbosity=0)
        else:
            runner = ansible_runner.run(private_data_dir='.attack_range/',
                               cmdline=str('-i ' + target_public_ip + ', '),
                               roles_path="../ansible/roles",
                               playbook='../ansible/playbooks/atomic_red_team.yml',
                               extravars={'run_specific_atomic_tests': run_specific_atomic_tests, 'art_run_tests': simulation_atomics, 'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['win_password'], 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
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

        if self.config['cloud_attack_range'] == '1':
            print()
            print('Status Serverless infrastructure\n')
            api_gateway_endpoint, error = aws_service.get_apigateway_endpoint(self.config)
            if not error:
                arr = []
                arr.append([api_gateway_endpoint['name'], str('https://' + api_gateway_endpoint['id'] + '.execute-api.' + self.config['region'] + '.amazonaws.com/prod/'), 'see Attack Range wiki for available REST API endpoints'])
                print(tabulate(arr,headers = ['Name', 'URL', 'Note']))
                print()
            else:
                print("ERROR: Can't find REST API Gateway.")

        if self.config['kubernetes'] == '1':
            print()
            print('Status Kubernetes\n')
            kubernetes_service.list_deployed_applications()
            print()

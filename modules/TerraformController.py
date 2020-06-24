
from modules.IEnvironmentController import IEnvironmentController
from python_terraform import *
from modules import aws_service, splunk_sdk, kubernetes_service
from tabulate import tabulate
import ansible_runner
import yaml
import time


class TerraformController(IEnvironmentController):

    def __init__(self, config, log, packer_amis):
        super().__init__(config, log)
        custom_dict = self.config.copy()
        rem_list = ['log_path', 'log_level', 'art_run_techniques', 'art_repository', 'art_branch', 'app', 'repo_name', 'repo_url']
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


    def search(self, search_name):
        instance = aws_service.get_instance_by_name("attack-range-splunk-server",self.config)
        if instance['State']['Name'] == 'running':
            splunk_sdk.test_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'],str(self.config['splunk_admin_password']), '| tstats `security_content_summariesonly` count min(_time) as firstTime max(_time) as lastTime from datamodel=Endpoint.Processes where (Processes.process_name=reg.exe OR Processes.process_name=cmd.exe) Processes.process=*save* (Processes.process=*HKEY_LOCAL_MACHINE\\Security* OR Processes.process=*HKEY_LOCAL_MACHINE\\SAM* OR Processes.process=*HKEY_LOCAL_MACHINE\\System* OR Processes.process=*HKLM\\Security* OR Processes.process=*HKLM\\System* OR Processes.process=*HKLM\\SAM*) by Processes.user Processes.process_name Processes.process Processes.dest | `drop_dm_object_name(Processes)` | `security_content_ctime(firstTime)`| `security_content_ctime(lastTime)` | `attempted_credential_dump_from_registry_via_reg_exe_filter`', '| stats count | where count = 6', 'Test detection', self.log)
        else:
            self.log.error('ERROR: Splunk server is not running.')

    def test(self, test_file):
        # read test file
        test_file = self.load_file(test_file)

        # build attack range
        #self.build()

        # simulate attack
        self.simulate(test_file['target'], test_file['simulation_technique'])

        # wait
        self.log.info('Wait for 600 seconds before running the detections.')
        time.sleep(600)

        # run detection
        result = []

        for detection_name in test_file['detections']:
            detection_file_name = detection_name.replace('-','_').replace(' ','_').lower() + '.yml'
            detection = self.load_file('../security-content/detections/' + detection_file_name)
            result_obj = dict()
            result_obj['detection'] = detection['name']
            instance = aws_service.get_instance_by_name("attack-range-splunk-server",self.config)
            if instance['State']['Name'] == 'running':
                result_obj['error'], result_obj['results'] = splunk_sdk.test_search(instance['NetworkInterfaces'][0]['Association']['PublicIp'], str(self.config['splunk_admin_password']), detection['search'], test_file['pass_condition'], detection['name'], self.log)
            else:
                self.log.error('ERROR: Splunk server is not running.')
            result.append(result_obj)

        #print(result)

        # destroy attack range
        #self.destroy()

        result_cond = False
        for result_obj in result:
            if result_obj['error']:
                self.log.error('Detection Testing failed: ' + result_obj['results']['detection_name'])
            result_cond |= result_obj['error']
        sys.exit(result_cond)


    def load_file(self, file_path):
        with open(file_path, 'r') as stream:
            try:
                file = list(yaml.safe_load_all(stream))[0]
            except yaml.YAMLError as exc:
                self.log.error(exc)
                sys.exit("ERROR: reading {0}".format(file_path))
        return file



    def simulate(self, target, simulation_techniques):
        target_public_ip = aws_service.get_single_instance_public_ip(target, self.config)
        if target == 'attack-range-windows-client':
            runner = ansible_runner.run(private_data_dir='.attack_range/',
                                   cmdline=str('-i ' + target_public_ip + ', '),
                                   roles_path="../ansible/roles",
                                   playbook='../ansible/playbooks/atomic_red_team.yml',
                                   extravars={'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['win_password'], 'ansible_port': 5985, 'ansible_winrm_scheme': 'http', 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
                                   verbosity=0)
        else:
            runner = ansible_runner.run(private_data_dir='.attack_range/',
                               cmdline=str('-i ' + target_public_ip + ', '),
                               roles_path="../ansible/roles",
                               playbook='../ansible/playbooks/atomic_red_team.yml',
                               extravars={'art_run_techniques': simulation_techniques, 'ansible_user': 'Administrator', 'ansible_password': self.config['win_password'], 'art_repository': self.config['art_repository'], 'art_branch': self.config['art_branch']},
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


    def list_searches(self):
        instance = aws_service.get_instance_by_name("attack-range-splunk-server",self.config)
        if instance['State']['Name'] == 'running':
            response = splunk_sdk.list_searches(instance['NetworkInterfaces'][0]['Association']['PublicIp'],str(self.config['splunk_admin_password']))
            if len(response) > 0:
                objects = []
                for object in response:
                    objects.append([object.name])
                print()
                print('Available savedsearches in Splunk\n')
                print(tabulate(objects, headers=['Name']))
                print()
        else:
            log.error('ERROR: Splunk server is not running.')

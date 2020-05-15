import subprocess
from jinja2 import Environment, FileSystemLoader
from modules import aws_service
import sys


def install_application(config, logger):

    update_kubeconfig_args = ['aws', 'eks', 'update-kubeconfig', '--name', str("kubernetes_" + config["key_name"])]
    logging_call(update_kubeconfig_args, logger)

    helm_load_repo_args = ['helm', 'repo', 'add', config["repo_name"], config["repo_url"]]
    logging_call(helm_load_repo_args, logger)

    helm_install_app_args = ['helm', 'install',  str("attack-range-" + config["app"]), str(config["repo_name"] + "/" + config["app"])]
    logging_call(helm_install_app_args, logger)

    splunk_ip = aws_service.get_splunk_instance_ip(config)

    j2_env = Environment(loader=FileSystemLoader('kubernetes/templates'),
                         trim_blocks=True)
    template = j2_env.get_template('splunkk8s.j2')
    output_path = 'kubernetes/splunkk8s.yaml'
    output = template.render(splunk_ip=splunk_ip)
    with open(output_path, 'w') as f:
        f.write(output)

    helm_install_splunk_connect_args = ['helm', 'install', 'splunk-connect', '-f', 'kubernetes/splunkk8s.yaml', 'https://github.com/splunk/splunk-connect-for-kubernetes/releases/download/1.4.1/splunk-connect-for-kubernetes-1.4.1.tgz']
    logging_call(helm_install_splunk_connect_args, logger)



def logging_call(popenargs, logger):

    process = subprocess.Popen(popenargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def check_io():
           while True:
                output = process.stdout.readline().decode()
                if output:
                    logger.info(output)
                else:
                    break

    # keep checking stdout/stderr until the child exits
    while process.poll() is None:
        check_io()



def delete_application(config, logger):
    helm_uninstall_app_args = ['helm', 'uninstall',  str("attack-range-" + config["app"])]
    logging_call(helm_uninstall_app_args, logger)

    helm_uninstall_splunk_args = ['helm', 'uninstall', 'splunk-connect']
    logging_call(helm_uninstall_splunk_args, logger)

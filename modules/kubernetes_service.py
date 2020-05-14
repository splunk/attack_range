import subprocess
from jinja2 import Environment, FileSystemLoader
from modules import aws_service


def install_wordpress_application(app, repo_name, repo, key_name, config):

    update_eks = subprocess.run(['aws', 'eks', 'update-kubeconfig', '--name', str("kubernetes_" + key_name)])
    helm_load_repo = subprocess.run(['helm', 'repo', 'add', repo_name, repo])
    helm_install_app = subprocess.run(['helm', 'install', str("attack-range-" + app), str(repo_name + "/" + app)])

    splunk_ip = aws_service.get_splunk_instance_ip(config)

    j2_env = Environment(loader=FileSystemLoader('kubernetes/templates'),
                         trim_blocks=True)
    template = j2_env.get_template('splunkk8s.j2')
    output_path = 'kubernetes/splunkk8s.yaml'
    output = template.render(splunk_ip=splunk_ip)
    with open(output_path, 'w') as f:
        f.write(output)

    helm_install_splunk_connect = subprocess.run(['helm', 'install', 'splunk-connect', '-f', 'kubernetes/splunkk8s.yaml', 'https://github.com/splunk/splunk-connect-for-kubernetes/releases/download/1.4.1/splunk-connect-for-kubernetes-1.4.1.tgz'])

import argparse
import wget
import re
import vagrant
import ansible_runner
from python_terraform import *

# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

VERSION = 1

def grab_splunk(bin_dir):
    print("\ngrabbing splunk enterprise server for linux\n")
    url = 'https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=linux&version=7.3.1&product=splunk&filename=splunk-7.3.1-bd63e13aa157-Linux-x86_64.tgz&wget=true'
    output = bin_dir + '/splunk-7.3.1-bd63e13aa157-Linux-x86_64.tgz'
    wget.download(url,output)

def grab_splunk_uf_win(bin_dir):
    print("\ngrabbing splunk forwarder for windows\n")
    url = 'https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&platform=windows&version=7.3.0&product=universalforwarder&filename=splunkforwarder-7.3.0-657388c7a488-x64-release.msi&wget=true'
    output = bin_dir + '/splunkforwarder-7.3.0-657388c7a488-x64-release.msi'
    wget.download(url,output)

def grab_splunk_ta_win(bin_dir):
    print("\ngrabbing splunk add-on for windows\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/splunk-add-on-for-microsoft-windows_600.tgz'
    output = bin_dir + '/splunk-add-on-for-microsoft-windows_600.tgz'
    wget.download(url, output)

def grab_splunk_ta_sysmon(bin_dir):
    print("\ngrabbing splunk add-on for sysmon\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/add-on-for-microsoft-sysmon_800.tgz'
    output = bin_dir + '/add-on-for-microsoft-sysmon_800.tgz'
    wget.download(url, output)

def grab_splunk_cim_app(bin_dir):
    print("\ngrabbing splunk (CIM) common information model app\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/splunk-common-information-model-cim_4130.tgz'
    output = bin_dir + '/splunk-common-information-model-cim_4130.tgz'
    wget.download(url, output)

def grab_streams(bin_dir):
    print("\ngrabbing splunk stream app\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/splunk-stream_713.tgz'
    output = bin_dir + '/splunk-stream_713.tgz'
    wget.download(url,output)
    print("\ngrabbing splunk stream TA\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/Splunk_TA_stream.zip'
    output = bin_dir + '/Splunk_TA_stream.zip'
    wget.download(url,output)

def grab_escu_latest(bin_dir):
    print("\ngrabbing splunk ESCU app\n")
    url = 'https://attack-range-appbinaries.s3-us-west-2.amazonaws.com/DA-ESS-ContentUpdate-v1.0.41.tar.gz'
    output = bin_dir + '/DA-ESS-ContentUpdate-v1.0.41.tar.gz'
    wget.download(url,output)


def config_simulation(simulation_engine, simulation_technique):

    # Read in the ansible vars file
    with open('ansible/vars/vars.yml', 'r') as file:
        ansiblevars = file.read()

    # now set the simulation engine and mitre techniques to run
    if simulation_engine == "atomic_red_team":
        ansiblevars = re.sub(r'install_art: \w+', 'install_art: true', ansiblevars, re.M)
        print("execution simulation using engine: {0}".format(simulation_engine))

    if simulation_technique[0] != '' or len(simulation_technique) > 1:
        technique = "art_run_technique: " + str(simulation_technique)
        ansiblevars = re.sub(r'art_run_technique: .+', technique, ansiblevars, re.M)
        ansiblevars = re.sub(r'art_run_all_test: \w+', 'art_run_all_test: false', ansiblevars, re.M)
        print("executing specific ATT&CK technique ID: {0}".format(simulation_technique))
    else:
        ansiblevars = re.sub(r'art_run_all_test: \w+', 'art_run_all_test: true', ansiblevars, re.M)
        print("executing ALL Atomic Red Team ATT&CK techniques see: https://github.com/redcanaryco/atomic-red-team/tree/master/atomics".format(
                simulation_technique))

    # Write the file out again
    with open('ansible/vars/vars.yml', 'w') as file:
        file.write(ansiblevars)


def run_simulation(mode, simulation_engine, host_ip):

    # read host file and replace the parameters
    with open('ansible/inventory/hosts.default', 'r') as file:
        hosts_file = file.read()

    # we need to change the port for ssh if we are running locally
    if mode == 'vagrant':
        hosts_file = hosts_file.replace('ansible_ssh_port=5986', 'ansible_ssh_port=5985')
        hosts_file = hosts_file.replace('ansible_ssh_user=Administrator', 'ansible_ssh_user = vagrant')
        hosts_file = hosts_file.replace('ansible_ssh_pass=myTempPassword123', 'ansible_ssh_pass = vagrant')
    hosts_file = hosts_file.replace('PUBLICIP', host_ip)

    # write hosts file to run from
    with open('ansible/inventory/hosts', 'w') as file:
        file.write(hosts_file)

    # execute atomic red team simulation
    if simulation_engine == "atomic_red_team":
        r = ansible_runner.run(private_data_dir='.attack_range/',
                               inventory=os.path.dirname(os.path.realpath(__file__)) + '/ansible/inventory/hosts',
                               roles_path="../roles",
                               playbook=os.path.dirname(os.path.realpath(__file__)) + '/ansible/playbooks/atomic_red_team.yml')
        print("{}: {}".format(r.status, r.rc))
        print("Final status:")
        print(r.stats)


def prep_ansible():
    # prep ansible for configuration
    # first we read from TF the win_username and password
    f = open("terraform/terraform.tfvars", "r")
    contents = f.read()

    win_password = re.findall(r'^win_password = \"(.+)\"', contents, re.MULTILINE)
    win_username = re.findall(r'^win_username = \"(.+)\"', contents, re.MULTILINE)

    # Read in the ansible vars file
    with open('ansible/vars/vars.yml', 'r') as file:
        ansiblevars = file.read()

    # Replace the username and password
    ansiblevars = ansiblevars.replace('USERNAME', win_username[0])
    ansiblevars = ansiblevars.replace('PASSWORD', win_password[0])

    # Write the file out again
    with open('ansible/vars/vars.yml', 'w') as file:
        file.write(ansiblevars)

    print("setting windows username: {0} from terraform/terraform.tfvars file".format(win_username))
    print("setting windows password: {0} from terraform/terraform.tfvars file".format(win_password))


def vagrant_mode(vbox, vagrant, action, simulation_engine, simulation_technique):
    # are we operating on a box or the entire range?
    if vbox:
        vagrantfile = 'vagrant/' + vbox
        print("operating on vagrant box: " + vagrantfile)
    else:
        vagrantfile = 'vagrant/'
        print("building splunk-server and windows10 workstation boxes WARNING MAKE SURE YOU HAVE 8GB OF RAM free otherwise you will have a bad time")

    if action == "build":
        print("[action] > build\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.up(provision=True)
        print("attack_range has been built using vagrant successfully")

    if action == "destroy":
        print ("[action] > destroy\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.destroy()
        print("attack_range has been destroy using vagrant successfully")

    if action == "simulate":
        hosts = []
        # lets get the host we have to run our simulations against
        # read in the vagrant file and grab out each IP from the hosts
        vagrantdata = list(open(vagrantfile + '/Vagrantfile', 'r').read().split('\n'))
        regex = r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}'
        for line in vagrantdata:
            matches = re.search(regex, line)
            if matches:
                hosts.append(matches.group())

        # lets configurate the simulation engine in ansible
        config_simulation(simulation_engine, simulation_technique)

        for h in hosts:
            if vagrantfile == 'vagrant/':
                print("running simulation against {0} operating on IP {1}".format('ALL machines', h))
            else:
                print("running simulation against {0} operating on IP IP {1}".format(vagrantfile, h))
            run_simulation('vagrant', simulation_engine, h)


def terraform_mode(Terraform, action):
    if action == "build":
        print ("[action] > build\n")
        t = Terraform(working_dir='terraform')
        return_code, stdout, stderr = t.apply(capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        print("attack_range has been built using terraform successfully")

    if action == "destroy":
        print ("[action] > destroy\n")
        t = Terraform(working_dir='terraform')
        return_code, stdout, stderr = t.destroy(capture_output='yes', no_color=IsNotFlagged)
        print("attack_range has been destroy using terraform successfully")

    if action == "simulate":
        config_simulation(simulation_engine, simulation_technique)


def list_vagrant_boxes():
    print("available VAGRANT BOX:\n")
    d = 'vagrant'
    subdirs = os.listdir(d)
    for f in subdirs:
        if f == ".vagrant" or f == "Vagrantfile":
            continue
        print("* " + f)
    sys.exit(1)


if __name__ == "__main__":
    # grab arguments
    parser = argparse.ArgumentParser(description="starts a attack range ready to collect attack data into splunk")
    parser.add_argument("-m", "--mode", required=True, default="terraform", choices=['vagrant', 'terraform'],
                        help="mode of operation, terraform/vagrant, please see configuration for each at: https://github.com/splunk/attack_range")
    parser.add_argument("-a", "--action", required=True, default="build", choices=['build', 'destroy', 'simulate'],
                        help="action to take on the range, defaults to \"build\", build/destroy/simulate allowed")
    parser.add_argument("-vls", "--vagrant_list", required=False, default=False, action="store_true",
                        help="prints out all available vagrant boxes")
    parser.add_argument("-vbox", "--vagrant_box", required=False, default="",
                        help="select which vagrant box to stand up or destroy individually")
    parser.add_argument("-se", "--simulation_engine", required=False, choices=['atomic_red_team'], default="atomic_red_team",
                        help="please select a simulation engine, defaults to \"atomic_red_team\"")
    parser.add_argument("-st", "--simulation_technique", required=False, type=str, default="",
                        help="comma delimited list of MITRE ATT&CK technique ID to simulate in the attack_range, example: T1117, T1118, requires --simulation flag")
    parser.add_argument("-b", "--appbin", required=False, default="appbinaries", help="directory to store binaries in")
    parser.add_argument("-v", "--version", required=False, help="shows current attack_range version")

    # parse them
    args = parser.parse_args()
    ARG_VERSION = args.version
    bin_dir = args.appbin
    mode = args.mode
    action = args.action
    vagrant_box = args.vagrant_box
    vagrant_list = args.vagrant_list
    simulation_engine = args.simulation_engine
    simulation_technique = [str(item) for item in args.simulation_technique.split(',')]



    print("INIT - Attack Range v" + str(VERSION))
    print("""
starting program loaded for mode - B1 battle droid
  ||/__'`.
  |//()'-.:
  |-.||
  |o(o)
  |||\\\  .==._
  |||(o)==::'
   `|T  ""
    ()
    |\\
    ||\\
    ()()
    ||//
    |//
   .'=`=.
    """)

    if ARG_VERSION:
        print("version: {0}".format(VERSION))
        sys.exit(1)

    if os.path.exists(bin_dir):
        print("this is not our first run binary directory exists, skipping setup")
    else:
        print("seems this is our first run, creating a directory for binaries at {0}".format(bin_dir))
        os.makedirs(bin_dir)
        grab_splunk(bin_dir)
        grab_splunk_uf_win(bin_dir)
        grab_splunk_ta_win(bin_dir)
        grab_splunk_ta_sysmon(bin_dir)
        grab_splunk_cim_app(bin_dir)
        grab_streams(bin_dir)
        grab_escu_latest(bin_dir)

    if vagrant_list:
        list_vagrant_boxes()

    if action != "simulate" and simulation_technique[0] != "":
        print("you must specify action simulate if using a simulation technique")
        parser.print_help()
        sys.exit(1)

    # lets process modes
    if mode == "vagrant":
        print("[mode] > vagrant")
        vagrant_mode(vagrant_box, vagrant, action, simulation_engine, simulation_technique)

    elif mode == "terraform":
        print("[mode] > terraform ")
        terraform_mode(Terraform, action, simulation_engine, simulation_technique)

    else:
        print("incorrect mode, please set flag --mode to \"terraform\" or \"vagrant\"")
        sys.exit(1)

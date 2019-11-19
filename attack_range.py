import argparse
import re
import vagrant
from python_terraform import *
from lib import logger

# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

VERSION = 1


def prep_ansible():
    # prep ansible for configuration
    # lets configure the passwords for ansible before we run any operations
    try:
        f = open("terraform/terraform.tfvars", "r")
        contents = f.read()

        win_password = re.findall(r'^win_password = \"(.+)\"', contents, re.MULTILINE)
        win_username = re.findall(r'^win_username = \"(.+)\"', contents, re.MULTILINE)

        # Read in the ansible vars file
        with open('ansible/vars/vars.yml.default', 'r') as file:
            ansiblevars = file.read()

        # Replace the username and password
        ansiblevars = ansiblevars.replace('USERNAME', win_username[0])
        ansiblevars = ansiblevars.replace('PASSWORD', win_password[0])

        # Write the file out again
        with open('ansible/vars/vars.yml', 'w') as file:
            file.write(ansiblevars)

        log.info("setting windows username: {0} from terraform/terraform.tfvars file".format(win_username))
        log.info("setting windows password: {0} from terraform/terraform.tfvars file".format(win_password))
    except e:
        log.error("make sure that ansible/host.default contains the windows username and password.\n" +
              "We were not able to set it automatically")

def check_state(state):
    if state == "up":
        pass
    elif state == "down":
        pass
    else:
        log.error("incorrect state, please set flag --state to \"up\" or \"download\"")
        sys.exit(1)


def vagrant_mode(vbox, vagrant, state):
    if vbox:
        vagrantfile = 'vagrant/' + vbox
        print("operating on vagrant box: " + vagrantfile)
    else:
        vagrantfile = 'vagrant/'
        print("operating on all range boxes WARNING MAKE SURE YOU HAVE 16GB OF RAM otherwise you will have a bad time")
    if state == "up":
        print ("[state] > up\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.up(provision=True)
        print("attack_range has been built using vagrant successfully")
    elif state == "down":
        print ("[state] > down\n")
        v1 = vagrant.Vagrant(vagrantfile, quiet_stdout=False)
        v1.destroy()
        print("attack_range has been destroy using vagrant successfully")

def terraform_mode(Terraform, state):
    if state == "up":
        print ("[state] > up\n")
        t = Terraform(working_dir='terraform')
        return_code, stdout, stderr = t.apply(capture_output='yes', skip_plan=True, no_color=IsNotFlagged)
        print("attack_range has been built using terraform successfully")

    if state == "down":
        print ("[state] > down\n")
        t = Terraform(working_dir='terraform')
        return_code, stdout, stderr = t.destroy(capture_output='yes', no_color=IsNotFlagged)
        print("attack_range has been destroy using terraform successfully")

def list_all_machines(log):
    log.info("available machines:\n")
    d = 'vagrant'
    subdirs = os.listdir(d)
    for f in subdirs:
        if f == ".vagrant" or f == "Vagrantfile":
            continue
        log.info("* " + f)
    sys.exit(1)

if __name__ == "__main__":
    # grab arguments
    parser = argparse.ArgumentParser(description="starts a attack range ready to collect attack data into splunk")
    parser.add_argument("-a", "--action", required=True, default="build", choices=['build', 'destroy', 'simulate'],
                        help="action to take on the range, defaults to \"build\", build/destroy/simulate allowed")
    parser.add_argument("-m", "--mode", required=True, default="terraform", choices=['vagrant', 'terraform'],
                        help="mode of operation, terraform/vagrant, please see configuration for each at: https://github.com/splunk/attack_range")
    parser.add_argument("-se", "--simulation_engine", required=False, choices=['atomic_red_team'], default="atomic_red_team",
                        help="please select a simulation engine, defaults to \"atomic_red_team\"")
    parser.add_argument("-st", "--simulation_technique", required=False, type=str, default="",
                        help="comma delimited list of MITRE ATT&CK technique ID to simulate in the attack_range, example: T1117, T1118, requires --simulation flag")
    parser.add_argument("-v", "--version", required=False, help="shows current attack_range version")
    parser.add_argument("-t", "--target", required=False, default="", help="select which machine to operate on. Only applicable to mode vagrant")
    parser.add_argument("-o", "--output", required=False, default="",
                        help="path to log file from the output of the range execution")
    parser.add_argument("-ls", "--list_machines", required=False, default=False, action="store_true", help="prints out all avaiable machines")


    # parse them
    args = parser.parse_args()
    ARG_VERSION = args.version
    mode = args.mode
    action = args.action
    target = args.target
    list_machines = args.list_machines

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

    log = logger.setup_logging(args.output, "INFO")
    log.info("INIT - Attack Range v" + str(VERSION))

    if ARG_VERSION:
        log.info("version: {0}".format(VERSION))
        sys.exit(1)

    if list_machines:
        list_all_machines(log)

    # lets process modes
    if mode == "vagrant":
        prep_ansible()
        log.info("[mode] > vagrant")
        vagrant_mode(target, vagrant, action)

    elif mode == "terraform":
        prep_ansible()
        log.info("[mode] > terraform ")
        terraform_mode(Terraform, action)

    else:
        log.error("incorrect mode, please set flag --mode to \"terraform\" or \"vagrant\"")
        sys.exit(1)





import os
import sys
import argparse
from modules import logger
from pathlib import Path
from modules.CustomConfigParser import CustomConfigParser
from modules.TerraformController import TerraformController
from modules.VagrantController import VagrantController
from modules.PackerController import PackerController


# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

VERSION = 1


if __name__ == "__main__":
    # grab arguments
    parser = argparse.ArgumentParser(description="starts a attack range ready to collect attack data into splunk")
    parser.add_argument("-m", "--mode", required=False, choices=['vagrant', 'terraform', 'packer'],
                        help="mode of operation, terraform/vagrant/packer, please see configuration for each at: https://github.com/splunk/attack_range")
    parser.add_argument("-a", "--action", required=False, choices=['build', 'destroy', 'simulate', 'stop', 'resume', 'search', 'build_amis', 'destroy_amis'],
                        help="action to take on the range, defaults to \"build\", build/destroy/simulate/stop/resume/search/build-amis/destroy_amis allowed")
    parser.add_argument("-t", "--target", required=False,
                        help="target for attack simulation. For mode vagrant use name of the vbox. For mode terraform use the name of the aws EC2 name")
    parser.add_argument("-st", "--simulation_technique", required=False, type=str, default="",
                        help="comma delimited list of MITRE ATT&CK technique ID to simulate in the attack_range, example: T1117, T1118, requires --simulation flag")
    parser.add_argument("-sn", "--search_name", required=False, type=str, default="",
                        help="name of savedsearch, which you want to run")
    parser.add_argument("-c", "--config", required=False, default="attack_range.conf",
                        help="path to the configuration file of the attack range")
    parser.add_argument("-lm", "--list_machines", required=False, default=False, action="store_true", help="prints out all available machines")
    parser.add_argument("-ls", "--list_searches", required=False, default=False, action="store_true", help="prints out all available savedsearches")
    parser.add_argument("-ami", required=False, default=False, action="store_true", help="use prebuilt packer amis with mode terraform")
    parser.add_argument("-v", "--version", default=False, action="store_true", required=False,
                        help="shows current attack_range version")

    # parse them
    args = parser.parse_args()
    ARG_VERSION = args.version
    mode = args.mode
    action = args.action
    target = args.target
    config = args.config
    simulation_techniques = args.simulation_technique
    list_machines = args.list_machines
    list_searches = args.list_searches
    search_name = args.search_name
    packer_amis = args.ami


    print("""
starting program loaded for B1 battle droid
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

    # parse config
    attack_range_config = Path(config)
    if attack_range_config.is_file():
        print("attack_range is using config at path {0}".format(attack_range_config))
        configpath = str(attack_range_config)
    else:
        print("ERROR: attack_range failed to find a config file at {0} or {1}..exiting".format(attack_range_config))
        sys.exit(1)

    # Parse config
    parser = CustomConfigParser()
    config = parser.load_conf(configpath)

    log = logger.setup_logging(config['log_path'], config['log_level'])
    log.info("INIT - attack_range v" + str(VERSION))

    if ARG_VERSION:
        log.info("version: {0}".format(VERSION))
        sys.exit(0)

    if not mode:
        log.error('ERROR: Specify Attack Range Mode with -m ')
        sys.exit(1)

    if mode and not action and not list_machines and not list_searches:
        log.error('ERROR: Use -a to perform an action or -lm to list available machines')
        sys.exit(1)

    if mode and action == 'simulate' and not target:
        log.error('ERROR: Specify target for attack simulation')
        sys.exit(1)

    if mode and action == 'search' and not search_name:
        log.error('ERROR: Specify search name to execute.')
        sys.exit(1)

    if mode != 'packer' and (action == 'build_amis' or action == 'destroy_amis'):
        log.error('ERROR: action build_amis and destroy_amis can only be used with packer')
        sys.exit(1)

    if mode != 'terraform' and packer_amis:
        log.error('ERROR: parameter packer_amis can only be used with terraform.')
        sys.exit(1)

    if mode == 'packer' and action != 'build_amis' and action != 'destroy_amis':
        log.error('ERROR: packer can only be used with action build_amis and destroy_amis. To build attack range use mode terraform or vagrant.')
        sys.exit(1)

    if mode != 'terraform' and (config['cloud_attack_range']=='1' or config['kubernetes']=='1'):
        log.error('ERROR: cloud_attack_range can only be used with mode terraform.')
        sys.exit(1)

    if config['cloud_attack_range']=='1' and config['cloud_s3_bucket']=="":
        log.error('ERROR: cloud_attack_range needs a value in cloud_s3_bucket, a s3_bucket in the same region of your attack_range containing the lambda function code e.g. backend.zip which can be found in https://attack-range-appbinaries.s3-us-west-2.amazonaws.com.')
        sys.exit(1)

    if config['cloud_attack_range']=='1' and config['cloudtrail']=='1' and config['cloudtrail_bucket']=="":
        log.error('ERROR: cloud_attack_range needs a value in cloudtrail_bucket, a s3_bucket in the same region of your attack_range to store the cloudtrail logs.')
        sys.exit(1)


    # lets give CLI priority over config file for pre-configured techniques
    if simulation_techniques:
        pass
    else:
        simulation_techniques = config['art_run_techniques']

    if mode == 'terraform':
        controller = TerraformController(config, log, packer_amis)
    elif mode == 'vagrant':
        controller = VagrantController(config, log)
    elif mode == 'packer':
        controller = PackerController(config, log)
        if action == 'build_amis':
            controller.build_amis()
        elif action == 'destroy_amis':
            controller.destroy_amis()

    if list_machines:
        controller.list_machines()
        sys.exit(0)

    if list_searches:
        controller.list_searches()
        sys.exit(0)

    if action == 'build':
        controller.build()

    if action == 'destroy':
        controller.destroy()

    if action == 'stop':
        controller.stop()

    if action == 'resume':
        controller.resume()

    if action == 'simulate':
        controller.simulate(target, simulation_techniques)

    if action == 'search':
        controller.search(search_name)





# rnfgre rtt ol C4G12VPX

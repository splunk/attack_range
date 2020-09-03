import os
import sys
import argparse
from modules import logger
from pathlib import Path
from modules.CustomConfigParser import CustomConfigParser
from modules.TerraformController import TerraformController


# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

VERSION = 1

def main(args):
    # grab arguments
    parser = argparse.ArgumentParser(description="starts a attack range ready to collect attack data into splunk")
    parser.add_argument("-a", "--action", required=False, choices=['build', 'destroy', 'simulate', 'stop', 'resume', 'test', 'dump'], default="",
                        help="action to take on the range, defaults to \"build\", build/destroy/simulate/stop/resume/search allowed")
    parser.add_argument("-t", "--target", required=False,
                        help="target for attack simulation. Use the name of the aws EC2 name")
    parser.add_argument("-st", "--simulation_technique", required=False, type=str, default="",
                        help="comma delimited list of MITRE ATT&CK technique ID to simulate in the attack_range, example: T1117, T1118, requires --simulation flag")
    parser.add_argument("-sa", "--simulation_atomics", required=False, type=str, default="",
                        help="specify dedicated Atomic Red Team atomics to simulate in the attack_range, example: Regsvr32 remote COM scriptlet execution for T1117")
    parser.add_argument("-dn", "--dump_name", required=False,
                        help="name for the dumped attack data")
    parser.add_argument("-c", "--config", required=False, default="attack_range.conf",
                        help="path to the configuration file of the attack range")
    parser.add_argument("-tf", "--test_file", required=False, type=str, default="", help='test file for test command')
    parser.add_argument("-lm", "--list_machines", required=False, default=False, action="store_true", help="prints out all available machines")
    parser.add_argument("-v", "--version", default=False, action="store_true", required=False,
                        help="shows current attack_range version")

    # parse them
    args = parser.parse_args()
    ARG_VERSION = args.version
    action = args.action
    target = args.target
    config = args.config
    simulation_techniques = args.simulation_technique
    simulation_atomics = args.simulation_atomics
    list_machines = args.list_machines
    test_file = args.test_file
    dump_name = args.dump_name

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
        print("ERROR: attack_range failed to find a config file")
        sys.exit(1)

    # Parse config
    parser = CustomConfigParser()
    config = parser.load_conf(configpath)

    log = logger.setup_logging(config['log_path'], config['log_level'])
    log.info("INIT - attack_range v" + str(VERSION))

    if ARG_VERSION:
        log.info("version: {0}".format(VERSION))
        sys.exit(0)

    if action == 'simulate' and not target:
        log.error('ERROR: Specify target for attack simulation')
        sys.exit(1)

    if action == 'test' and not test_file:
        log.error('ERROR: Specify test file --test_file to execute.')
        sys.exit(1)

    if action == "" and not list_machines:
        log.error('ERROR: flag --action is needed.')
        sys.exit(1)

    if config['attack_range_password'] == 'Pl3ase-k1Ll-me:p':
        log.error('ERROR: please change attack_range_password in attack_range.conf')
        sys.exit(1)


    # lets give CLI priority over config file for pre-configured techniques
    if simulation_techniques:
        pass
    else:
        simulation_techniques = config['art_run_techniques']

    if not simulation_atomics:
        simulation_atomics = 'no'

    # default to terraform
    controller = TerraformController(config, log)

    if list_machines:
        controller.list_machines()
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
        controller.simulate(target, simulation_techniques, simulation_atomics)

    if action == 'test':
        return controller.test(test_file)

    if action == 'dump':
        controller.dump_attack_data(dump_name)


if __name__ == "__main__":
    main(sys.argv[1:])


# rnfgre rtt ol C4G12VPX

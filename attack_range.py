import os
import sys
import argparse

from colorama import Fore, Back, Style

from modules.config_handler import ConfigHandler
from modules.aws_controller import AwsController
from modules.azure_controller import AzureController

# need to set this ENV var due to a OSX High Sierra forking bug
# see this discussion for more details: https://github.com/ansible/ansible/issues/34056#issuecomment-352862252
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'


def init(args):
    config_path = args.config
    print(Back.BLACK + Fore.GREEN + """
starting program loaded for B1 battle droid """ + Back.BLACK + Fore.BLUE + Style.BRIGHT + """
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
    config = ConfigHandler.read_config(config_path)
    ConfigHandler.validate_config(config)

    if config['general']['cloud_provider'] == 'aws':
        config.pop('azure')
        controller = AwsController(config)
    elif config['general']['cloud_provider'] == 'azure':
        config.pop('aws')
        controller = AzureController(config)
   
    return controller


def simulate(args):
    controller = init(args)
    controller.simulate(args.engine, args.target, args.technique, args.playbook)

def dump(args):
    controller = init(args)
    controller.dump(args.file_name, args.search, args.earliest, args.latest)

def replay(args):
    controller = init(args)
    controller.replay(args.file_name, args.index, args.sourcetype, args.source)

def build(args):
    controller = init(args)
    controller.build()

def destroy(args):
    controller = init(args)
    controller.destroy()

def stop(args):
    controller = init(args)
    controller.stop()
    
def resume(args):
    controller = init(args)
    controller.resume()

def configure(args):
    pass

def show(args):
    controller = init(args)
    controller.show()


def main(args):
    # grab arguments
    parser = argparse.ArgumentParser(
        description="Use `attack_range.py action -h` to get help with any Attack Range action")
    parser.add_argument("-c", "--config", required=False, default="attack_range.yml",
                        help="path to the configuration file of the attack range")
    parser.set_defaults(func=lambda _: parser.print_help())

    actions_parser = parser.add_subparsers(title="attack Range actions", dest="action")
    configure_parser = actions_parser.add_parser("configure", help="configure a new attack range")
    build_parser = actions_parser.add_parser("build", help="builds attack range instances")
    simulate_parser = actions_parser.add_parser("simulate", help="simulates attack techniques")
    destroy_parser = actions_parser.add_parser("destroy", help="destroy attack range instances")
    stop_parser = actions_parser.add_parser("stop", help="stops attack range instances")
    resume_parser = actions_parser.add_parser("resume", help="resumes previously stopped attack range instances")
    show_parser = actions_parser.add_parser("show", help="list machines")
    dump_parser = actions_parser.add_parser("dump", help="dump locally logs from attack range instances")
    replay_parser = actions_parser.add_parser("replay", help="replay dumps into the splunk server")

    # Build arguments
    build_parser.set_defaults(func=build)

    # Destroy arguments
    destroy_parser.set_defaults(func=destroy)

    # Stop arguments
    stop_parser.set_defaults(func=stop)

    # Resume arguments
    resume_parser.set_defaults(func=resume)

    # Configure arguments
    configure_parser.add_argument("-c", "--config", required=False, type=str, default='attack_range.yml',
                                    help="provide path to write configuration to")
    configure_parser.set_defaults(func=configure)

    # Simulation arguments
    simulate_parser.add_argument("-e", "--engine", required=False, default="ART",
                                 help="simulation engine to use. Available options are: PurpleSharp and ART (default)")
    simulate_parser.add_argument("-t", "--target", required=True,
                                 help="target for attack simulation. Use the name of the aws EC2 name")
    simulate_parser.add_argument("-te", "--technique", required=True, type=str, default="",
                                 help="comma delimited list of MITRE ATT&CK technique ID to simulate in the "
                                      "attack_range, example: T1117, T1118")
    simulate_parser.add_argument("-p", "--playbook", required=False, type=str, default="",
                                 help="file path for a PurpleSharp JSON simulation playbook")

    simulate_parser.set_defaults(func=simulate)

    # Dump  Arguments
    dump_parser.add_argument("-fn", "--file_name", required=True,
                               help="file name of the attack_data")
    dump_parser.add_argument("--search", required=True,
                             help="splunk search to export")
    dump_parser.add_argument("--earliest", required=True,
                             help="earliest time of the splunk search")
    dump_parser.add_argument("--latest", required=False, default="now",
                             help="latest time of the splunk search")
    dump_parser.set_defaults(func=dump)

    # Replay Arguments
    replay_parser.add_argument("-fn", "--file_name", required=True,
                               help="file name of the attack_data")
    replay_parser.add_argument("--source", required=True,
                        help="source of replayed data")
    replay_parser.add_argument("--sourcetype", required=True,
                        help="sourcetype of replayed data")
    replay_parser.add_argument("--index", required=False, default="test",
                        help="index of replayed data")
    replay_parser.set_defaults(func=replay)


    # Show arguments
    show_parser.add_argument("-m", "--machines", required=False, default=False,
                             action="store_true", help="prints out all available machines")
    show_parser.set_defaults(func=show, machines=True)

    # # parse them
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
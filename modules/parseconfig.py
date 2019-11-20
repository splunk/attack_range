import configparser
import collections
import sys

class parser:
    def __init__(self):
        self.settings = collections.defaultdict(dict)

    def load_conf(self,CONFIG_PATH):
        """Provided a config file path and a collections of type dict,
        will return that collections with all the settings in it"""
        config = configparser.RawConfigParser()
        config.read(CONFIG_PATH)
        sections = config.sections()

        try:
            #grab log path
            if config.get('global', 'log_path'):
                self.settings['LOG_PATH'] = config.get('global', 'log_path')
            else:
                self.settings['LOG_PATH'] = 'attack_range.log'
            #grab log level
            if config.get('global', 'log_level'):
                self.settings['LOG_LEVEL'] = config.get('global', 'log_level')
            else:
                self.settings['LOG_LEVEL'] = 'INFO'

            #grab range settings
            if config.get('range_settings','key_name'):
                self.settings['KEY_NAME'] = config.get('range_settings','key_name')
            else:
                print("ssh key name is required, please refer to https://github.com/splunk/attack_range/wiki/Configure-Attack-Range-for-Terraform for more details")
                sys.exit(1)
            if config.get('range_settings', 'aws_region'):
                self.settings['AWS_REGION'] = config.get('range_settings', 'aws_region')
            else:
                print("requires a aws region to be defined in the config")
                sys.exit(1)
            if config.get('range_settings', 'ip_whitelist'):
                    self.settings['IP_WHITELIST'] = config.get('range_settings', 'ip_whitelist')
            else:
                print("requires a ip_whitelist be defined on the config in the form of an array and CIDR notation eg [\"1.1.1.1/32\",\"2.2.2.2\"]")
                sys.exit(1)
            if config.get('range_settings','win_username'):
                self.settings['WIN_USERNAME'] = config.get('range_settings','win_username')
            else:
                print("requires a windows username be defined in the config")
                sys.exit(1)
            if config.get('range_settings','win_username'):
                self.settings['WIN_USERNAME'] = config.get('range_settings','win_username')
            else:
                print("requires a windows username be defined in the config")
                sys.exit(1)
            if config.get('range_settings', 'win_password'):
                self.settings['WIN_PASSWORD'] = config.get('range_settings', 'win_password')
            else:
                print("requires a windows password be defined in the config")
                sys.exit(1)
            if config.get('range_settings','private_key_path'):
                self.settings['PRIVATE_KEY_PATH'] = config.get('range_settings','private_key_path')
            else:
                print("path to the private key path that will be used to ssh into range hosts, refer to https://github.com/splunk/attack_range/wiki/Configure-Attack-Range-for-Terraform for more details")
                sys.exit(1)

            # splunk parameters
            if config.get('range_settings','s3_bucket_url'):
                self.settings['S3_BUCKET'] = config.get('range_settings','s3_bucket_url')
            else:
                print("requires a s3 bucket url be defined in the config")
                sys.exit(1)
            if config.get('range_settings','splunk_admin_password'):
                self.settings['SPLUNK_ADMIN_PASSWORD'] = config.get('range_settings','splunk_admin_password')
            else:
                print("requires a splunk admin password be defined in the config")
                sys.exit(1)
            if config.get('range_settings','splunk_windows_ta'):
                self.settings['SPLUNK_WINDOWS_TA'] = config.get('range_settings','splunk_windows_ta')
            else:
                print("requires a splunk windows TA name be defined in the config")
                sys.exit(1)
            if config.get('range_settings', 'splunk_sysmon_ta'):
                self.settings['SPLUNK_SYSMON_TA'] = config.get('range_settings', 'splunk_sysmon_ta')
            else:
                print("requires a splunk sysmon TA name be defined in the config")
                sys.exit(1)
            if config.get('range_settings', 'splunk_stream_ta'):
                self.settings['SPLUNK_STREAM_TA'] = config.get('range_settings', 'splunk_stream_ta')
            else:
                print("requires a splunk streams TA name be defined in the config")
                sys.exit(1)
            if config.get('range_settings', 'splunk_stream_app'):
                self.settings['SPLUNK_STREAM_APP'] = config.get('range_settings', 'splunk_stream_app')
            else:
                print("requires a splunk stream app name be defined in the config")
                sys.exit(1)
            if config.get('range_settings', 'splunk_cim_app'):
                self.settings['SPLUNK_CIM_APP'] = config.get('range_settings', 'splunk_cim_app')
            else:
                print("requires a splunk CIM app name be defined in the config")
                sys.exit(1)
            if config.get('range_settings', 'splunk_escu_app'):
                self.settings['SPLUNK_ESCU_APP'] = config.get('range_settings', 'splunk_escu_app')
            else:
                print("requires a splunk ESCU app name be defined in the config")
                sys.exit(1)

            # grab simulation settings
            if config.get('simulation', 'simulation_engine'):
                self.settings['SIMULATION_ENGINE'] = config.get('simulation', 'simulation_engine')
            else:
                print("requires a simulation engine be defined in the config")
                sys.exit(1)
            # grab simulation settings
            if config.get('simulation', 'simulation_technique'):
                self.settings['SIMULATION_TECHNIQUE'] = config.get('simulation', 'simulation_technique')
        except Exception as e:
            print("ERROR - with configuration file at {0} failed with error {1}".format(CONFIG_PATH, e))
            sys.exit(1)
        return self.settings

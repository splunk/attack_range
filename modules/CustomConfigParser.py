import configparser
import collections
import sys

class CustomConfigParser:
    def __init__(self):
        #self.settings = collections.defaultdict(dict)
        self.settings = {}

    def load_conf(self,CONFIG_PATH):
        """Provided a config file path and a collections of type dict,
        will return that collections with all the settings in it"""

        config = configparser.RawConfigParser()
        config.read('default/attack_range.conf.default')
        config.read(CONFIG_PATH)
        sections = config.sections()

        for section in config.sections():
            for key in config[section]:
                try:
                    self.settings[key] = self.perform_lookup(key,config.get(section, key))
                except Exception as e:
                    print("ERROR - with configuration file at {0} failed with error {1}".format(CONFIG_PATH, e))
                    sys.exit(1)
        return self.settings

    def perform_lookup(self, config_key, config_value):
        if config_key == 'windows_domain_controller_os' or config_key == 'windows_server_os':
            if config_value == 'Windows_Server_2016':
                return 'Windows_Server-2016-English-Full-Base-2019.12.16'
            else:
                return 'Windows_Server-2016-English-Full-Base-2019.12.16'
        else:
            return config_value

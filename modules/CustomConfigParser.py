import configparser
import collections
import sys

class CustomConfigParser:
    def __init__(self):
        self.settings = {}

    def _config_rules(self, CONFIG_PATH):
        if self.settings['windows_domain_controller'] == "0" and self.settings['windows_server_join_domain'] == "1":
            print("ERROR - with configuration file at {0} 'windows_server_join_domain' cannot be '1' if the number of "
                  "'windows_domain_controller' is set to '0'".format(CONFIG_PATH))
            sys.exit(1)

    def load_conf(self,CONFIG_PATH):
        """Provided a config file path and a collections of type dict,
        will return that collections with all the settings in it"""

        config = configparser.RawConfigParser()
        config.read(CONFIG_PATH)
        for section in config.sections():
            for key in config[section]:
                try:
                    self.settings[key] = config.get(section, key)
                except Exception as e:
                    print("ERROR - with configuration file at {0} failed with error {1}".format(CONFIG_PATH, e))
                    sys.exit(1)
        self._config_rules(CONFIG_PATH)

        return self.settings

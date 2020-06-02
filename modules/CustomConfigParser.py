import configparser
import collections
import sys
from pathlib import Path
import re

class CustomConfigParser:
    def __init__(self):
        self.settings = {}

    def _config_rules(self, CONFIG_PATH):
        if self.settings['windows_domain_controller'] == "0" and self.settings['windows_server_join_domain'] == "1":
            print("ERROR - with configuration file at {0} 'windows_server_join_domain' must be set to '0' "
                  "if the number of 'windows_domain_controller' is set to '0'".format(CONFIG_PATH))
            sys.exit(1)

        # lets load the dsp certificate if enabled
        if self.settings['install_dsp'] == "1":
            dsp_client_cert_path = Path(self.settings['dsp_client_cert_path'])
            if dsp_client_cert_path.is_file():
                print("attack_range loaded dsp client certificate from path: {0}".format(dsp_client_cert_path.absolute()))
                self.settings['dsp_client_cert_path'] = str(dsp_client_cert_path.absolute())
            else:
                print("ERROR - with configuration file at: {0}, failed to load dsp client certificate \
                        from path: {1} and install_dsp is enabled".format(CONFIG_PATH, dsp_client_cert_path))
                sys.exit(1)

        key_name_regex = re.compile('[@!#$%^&*()<>?/\|}{~:]') 
        if (key_name_regex.search(self.settings['key_name']) != None):
            print("ERROR - with configuration file at: {0}, no special characters allowed for key_name: {1}".format(CONFIG_PATH,self.settings['key_name']))
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

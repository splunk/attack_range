import os
import collections

from modules.yml_reader import YmlReader


class ConfigHandler:

    @classmethod
    def read_config(self, config_path: str) -> dict:
        yml_dict = YmlReader.load_file(os.path.join(os.path.dirname(__file__), '../', config_path))
        return yml_dict

    @classmethod
    def validate_config(self, yml_dict: dict) -> None:
        # do validation here
        pass
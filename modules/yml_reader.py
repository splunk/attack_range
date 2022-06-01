import yaml
import sys

class YmlReader():

    @staticmethod
    def load_file(file_path: str) -> dict:
        try:
            file_handler = open(file_path, 'r', encoding="utf-8")
            try:
                yml_obj = list(yaml.safe_load_all(file_handler))[0]
            except yaml.YAMLError as exc:
                print(exc)
                sys.exit(1)

        except OSError as exc:
            print(exc)
            sys.exit(1)

        return yml_obj
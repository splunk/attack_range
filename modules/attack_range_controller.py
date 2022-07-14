import abc
import os

from modules import logger


class AttackRangeController(abc.ABC):

    @abc.abstractmethod
    def __init__(self, config: dict):
        self.config = config
        self.logger = logger.setup_logging(
            os.path.join(os.path.dirname(__file__), '../attack_range.log'), 
            'INFO'
        )

    @abc.abstractmethod
    def build(self) -> None:
        pass

    @abc.abstractmethod
    def destroy(self) -> None:
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        pass

    @abc.abstractmethod
    def resume(self) -> None:
        pass

    @abc.abstractmethod
    def packer(self, image_name) -> None:
        pass

    @abc.abstractmethod
    def simulate(self, engine, target, technique, playbook) -> None:
        pass

    @abc.abstractmethod
    def show(self) -> None:
        pass

    @abc.abstractmethod
    def dump(self, dump_name, search, earliest, latest) -> None:
        pass

    @abc.abstractmethod
    def replay(self, file_name, index, sourcetype, source) -> None:
        pass

    @abc.abstractmethod
    def create_remote_backend(self, backend_name) -> None:
        pass

    @abc.abstractmethod
    def delete_remote_backend(self, backend_name) -> None:
        pass

    @abc.abstractmethod
    def init_remote_backend(self, backend_name) -> None:
        pass
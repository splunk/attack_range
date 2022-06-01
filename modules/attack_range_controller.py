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
    def simulate(self, engine, target, technique, playbook) -> None:
        pass


    @abc.abstractmethod
    def show(self) -> None:
        pass

import abc

class SimulationController(abc.ABC):

    def __init__(self, config: dict):
        self.config = config

    @abc.abstractmethod
    def simulate(self) -> None:
        pass
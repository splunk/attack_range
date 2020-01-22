
from abc import ABC, abstractmethod

class IEnvironmentController(ABC):


    def __init__(self, config, log):
        self.config = config
        self.log = log
        super().__init__()

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def destroy(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def resume(self):
        pass

    @abstractmethod
    def simulate(self, target, simulation_techniques):
        pass

    @abstractmethod
    def search(self, search_name):
        pass

    @abstractmethod
    def list_machines(self):
        pass

    @abstractmethod
    def list_searches(self):
        pass

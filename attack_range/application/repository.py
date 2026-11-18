"""Repository port: where the documents of a cyber range come from."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from attack_range.domain.entities.common import Provider

from .cyber_range import CyberRange


class CyberRangeRepository(ABC):
    @abstractmethod
    def load(self, location: Path, provider: Optional[Provider] = None) -> CyberRange:
        """Load the cyber range at `location` with the bindings of `provider`.

        Raises CyberRangeError when the documents are invalid or do not fit together.
        """

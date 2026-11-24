"""Repository port: where the documents of a cyber range come from."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from attack_range.domain.entities.common import Provider

from .cyber_range import CyberRange, Document


class CyberRangeRepository(ABC):
    @abstractmethod
    def load(self, location: Path, provider: Optional[Provider] = None) -> CyberRange:
        """Load the cyber range at `location` with the bindings of `provider`.

        Raises CyberRangeError when the documents are invalid or do not fit together.
        """

    @abstractmethod
    def read(self, location: Path) -> tuple[list[Document], dict[str, str]]:
        """Read the documents at `location` and the user-data files they name.

        Does not check that the documents form a complete cyber range. Raises CyberRangeError
        when a file cannot be parsed or when `location` has no documents.
        """

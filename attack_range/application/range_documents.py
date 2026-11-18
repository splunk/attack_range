"""Range documents port: the copy of a template that a registered range is built from."""

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from attack_range.domain.entities.common import Provider

from .cyber_range import CyberRange


class RangeDocuments(ABC):
    @abstractmethod
    def import_documents(self, range_id: UUID, source: Path) -> None:
        """Copy the documents at `source`, a directory or a single file, to the range."""

    @abstractmethod
    def load(self, range_id: UUID, provider: Provider) -> CyberRange:
        """Load the range's own copy of its documents. The result carries `range_id`.

        Raises CyberRangeError when the documents are missing or invalid.
        """

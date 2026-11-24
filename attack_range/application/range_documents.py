"""Range documents port: the copy of a template that a registered range is built from."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence
from uuid import UUID

from attack_range.domain.entities.common import Provider

from .cyber_range import CyberRange, Document


class RangeDocuments(ABC):
    @abstractmethod
    def import_documents(self, range_id: UUID, source: Path) -> None:
        """Copy the documents at `source`, a directory or a single file, to the range."""

    @abstractmethod
    def paths(self, range_id: UUID) -> list[Path]:
        """Absolute paths of the YAML documents and user-data files stored for the range."""

    @abstractmethod
    def load(self, range_id: UUID, provider: Provider) -> CyberRange:
        """Load the range's own copy of its documents. The result carries `range_id`.

        Raises CyberRangeError when the documents are missing or invalid.
        """

    @abstractmethod
    def read(self, range_id: UUID) -> tuple[list[Document], dict[str, str]]:
        """Return the range's documents and the user-data files stored with them."""

    @abstractmethod
    def replace(
        self, range_id: UUID, documents: Sequence[Document], bootstrap_files: dict[str, str]
    ) -> None:
        """Replace the range's documents with `documents`, keeping `bootstrap_files` beside them."""

    @abstractmethod
    def delete(self, range_id: UUID) -> None:
        """Remove the range's copy of its documents. Does nothing when there is none."""

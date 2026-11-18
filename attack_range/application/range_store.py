"""Range store port: the registry of built cyber ranges and their lifecycle state."""

from abc import ABC, abstractmethod
from uuid import UUID

from attack_range.domain.entities.range_record import RangeRecord


class RangeNotFound(LookupError):
    """Raised when no range is registered under an id."""


class RangeStore(ABC):
    """Keeps one RangeRecord per range. Files, a database, or memory can implement it."""

    @abstractmethod
    def create(self, record: RangeRecord) -> None:
        """Register a new range. Raises ValueError when the id is taken."""

    @abstractmethod
    def get(self, range_id: UUID) -> RangeRecord:
        """Return the record of `range_id` or raise RangeNotFound."""

    @abstractmethod
    def update(self, record: RangeRecord) -> None:
        """Replace the stored record with the same id. Raises RangeNotFound when there is none."""

    @abstractmethod
    def list(self) -> list[RangeRecord]:
        """Return every registered range, in no particular order."""

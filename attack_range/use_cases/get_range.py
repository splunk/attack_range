"""Show one registered cyber range."""

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from attr import define

from attack_range.application.cyber_range import CyberRange, CyberRangeError
from attack_range.application.range_documents import RangeDocuments
from attack_range.application.range_store import RangeNotFound, RangeStore
from attack_range.domain.entities.range_record import RangeRecord


@dataclass(frozen=True)
class GetRangeInputDto:
    range_id: UUID


@dataclass(frozen=True)
class GetRangeOutputDto:
    success: bool
    range_id: UUID
    record: Optional[RangeRecord] = None
    cyber_range: Optional[CyberRange] = None
    error: Optional[str] = None
    documents_error: Optional[str] = None
    """Set when the record exists but its documents cannot be read."""
    files: tuple[Path, ...] = field(default_factory=tuple)
    """YAML documents and user-data files stored for the range."""


class GetRangeOutputBoundary(abc.ABC):
    @abc.abstractmethod
    def present(self, dto: GetRangeOutputDto) -> None:
        pass

    @abc.abstractmethod
    def get_presented_value(self) -> Any:
        pass


@define
class GetRange:
    """Load one range and the documents it was built from."""

    _output_boundary: GetRangeOutputBoundary
    _documents: RangeDocuments
    _store: RangeStore

    def execute(self, input_dto: GetRangeInputDto) -> None:
        try:
            record = self._store.get(input_dto.range_id)
        except (RangeNotFound, ValueError) as error:
            self._output_boundary.present(GetRangeOutputDto(
                success=False, range_id=input_dto.range_id, error=str(error),
            ))
            return
        files = self._files(record.id)
        try:
            cyber_range = self._documents.load(record.id, record.provider)
        except (CyberRangeError, OSError, ValueError) as error:
            self._output_boundary.present(GetRangeOutputDto(
                success=True, range_id=record.id, record=record, documents_error=str(error), files=files,
            ))
            return
        self._output_boundary.present(GetRangeOutputDto(
            success=True, range_id=record.id, record=record, cyber_range=cyber_range, files=files,
        ))

    def _files(self, range_id: UUID) -> tuple[Path, ...]:
        try:
            return tuple(self._documents.paths(range_id))
        except (CyberRangeError, OSError, ValueError):
            return ()

import abc
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from uuid import UUID

from attr import define
from attr import field as attr_field

from attack_range.application.range_documents import RangeDocuments
from attack_range.application.range_store import RangeStore
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState

RETENTION = timedelta(days=30)


@dataclass(frozen=True)
class PruneRangesInputDto:
    older_than: timedelta = RETENTION
    """Delete ranges that were destroyed longer ago than this."""


@dataclass(frozen=True)
class PruneRangesOutputDto:
    older_than: timedelta
    deleted: list[RangeRecord] = field(default_factory=list)
    failed: dict[UUID, str] = field(default_factory=dict)
    """Ranges that could not be deleted, with the reason. They are tried again next time."""


class PruneRangesOutputBoundary(abc.ABC):
    @abc.abstractmethod
    def present(self, dto: PruneRangesOutputDto) -> None:
        pass

    @abc.abstractmethod
    def get_presented_value(self) -> Any:
        pass


def _now() -> datetime:
    return datetime.now(UTC)


@define
class PruneRanges:
    """Delete the records and documents of ranges that were destroyed long enough ago."""

    _output_boundary: PruneRangesOutputBoundary
    _store: RangeStore
    _documents: RangeDocuments
    _clock: Callable[[], datetime] = attr_field(default=_now)

    def execute(self, input_dto: PruneRangesInputDto) -> None:
        cutoff = self._clock() - input_dto.older_than
        deleted: list[RangeRecord] = []
        failed: dict[UUID, str] = {}
        for record in self._store.list():
            if record.state is not RangeState.DESTROYED or record.updated_at >= cutoff:
                continue
            try:
                self._documents.delete(record.id)
                self._store.delete(record.id)
            except Exception as error:  # noqa: BLE001 - housekeeping must not stop the command that runs it
                failed[record.id] = str(error)
            else:
                deleted.append(record)
        self._output_boundary.present(
            PruneRangesOutputDto(older_than=input_dto.older_than, deleted=deleted, failed=failed)
        )

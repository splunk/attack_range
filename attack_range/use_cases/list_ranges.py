import abc
from dataclasses import dataclass
from typing import Any

from attr import define

from attack_range.application.range_store import RangeStore
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState


@dataclass(frozen=True)
class ListRangesInputDto:
    include_destroyed: bool = False


@dataclass(frozen=True)
class ListRangesOutputDto:
    ranges: list[RangeRecord]
    hidden: int = 0
    """How many destroyed ranges were left out."""


class ListRangesOutputBoundary(abc.ABC):
    @abc.abstractmethod
    def present(self, dto: ListRangesOutputDto) -> None:
        pass

    @abc.abstractmethod
    def get_presented_value(self) -> Any:
        pass


@define
class ListRanges:
    """Show the registered ranges, oldest first."""

    _output_boundary: ListRangesOutputBoundary
    _store: RangeStore

    def execute(self, input_dto: ListRangesInputDto) -> None:
        records = sorted(self._store.list(), key=lambda record: record.created_at)
        shown = [
            record for record in records
            if input_dto.include_destroyed or record.state is not RangeState.DESTROYED
        ]
        self._output_boundary.present(ListRangesOutputDto(ranges=shown, hidden=len(records) - len(shown)))

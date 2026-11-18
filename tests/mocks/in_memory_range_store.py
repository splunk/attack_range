from uuid import UUID

from attack_range.application.range_store import RangeNotFound, RangeStore
from attack_range.domain.entities.range_record import RangeRecord


class InMemoryRangeStore(RangeStore):
    """Keeps records in a dict and remembers every state that was stored."""

    def __init__(self) -> None:
        self.records: dict[UUID, RangeRecord] = {}
        self.stored_states: list[str] = []

    def create(self, record: RangeRecord) -> None:
        if record.id in self.records:
            raise ValueError(f"a cyber range with id {record.id} already exists")
        self._put(record)

    def get(self, range_id: UUID) -> RangeRecord:
        try:
            return self.records[range_id]
        except KeyError:
            raise RangeNotFound(f"no cyber range with id {range_id}") from None

    def update(self, record: RangeRecord) -> None:
        if record.id not in self.records:
            raise RangeNotFound(f"no cyber range with id {record.id}")
        self._put(record)

    def list(self) -> list[RangeRecord]:
        return list(self.records.values())

    def _put(self, record: RangeRecord) -> None:
        self.records[record.id] = record
        self.stored_states.append(record.state.value)

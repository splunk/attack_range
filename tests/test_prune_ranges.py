from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence
from uuid import UUID

import pytest

from attack_range.application.cyber_range import CyberRange, Document
from attack_range.application.range_documents import RangeDocuments
from attack_range.domain.entities.common import Provider
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState
from attack_range.use_cases.prune_ranges import (
    PruneRanges,
    PruneRangesInputDto,
    PruneRangesOutputBoundary,
    PruneRangesOutputDto,
)
from mocks.in_memory_range_store import InMemoryRangeStore

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
LIFECYCLE = {
    RangeState.BUILT: [RangeState.BUILDING, RangeState.BUILT],
    RangeState.BUILD_FAILED: [RangeState.BUILDING, RangeState.BUILD_FAILED],
    RangeState.DESTROY_FAILED: [RangeState.BUILDING, RangeState.BUILT, RangeState.DESTROYING, RangeState.DESTROY_FAILED],
    RangeState.DESTROYED: [RangeState.BUILDING, RangeState.BUILT, RangeState.DESTROYING, RangeState.DESTROYED],
}


class RecordingDocuments(RangeDocuments):
    def __init__(self, fail_for: Optional[UUID] = None) -> None:
        self.deleted: list[UUID] = []
        self._fail_for = fail_for

    def import_documents(self, range_id: UUID, source: Path) -> None:
        raise NotImplementedError

    def paths(self, range_id: UUID) -> list[Path]:
        return []

    def load(self, range_id: UUID, provider: Provider) -> CyberRange:
        raise NotImplementedError

    def read(self, range_id: UUID) -> tuple[list[Document], dict[str, str]]:
        raise NotImplementedError

    def replace(
        self, range_id: UUID, documents: Sequence[Document], bootstrap_files: dict[str, str]
    ) -> None:
        raise NotImplementedError

    def delete(self, range_id: UUID) -> None:
        if range_id == self._fail_for:
            raise PermissionError("read-only")
        self.deleted.append(range_id)


class RecordingBoundary(PruneRangesOutputBoundary):
    def __init__(self) -> None:
        self.presented: Optional[PruneRangesOutputDto] = None

    def present(self, dto: PruneRangesOutputDto) -> None:
        self.presented = dto

    def get_presented_value(self) -> Optional[PruneRangesOutputDto]:
        return self.presented


def add(store: InMemoryRangeStore, state: RangeState, days_ago: float) -> RangeRecord:
    record = RangeRecord.new(name=f"{state}-{days_ago}", provider="aws", location="eu-central-1", source="/t")
    for step in LIFECYCLE[state]:
        record = record.transition(step)
    record = record.model_copy(update={"updated_at": NOW - timedelta(days=days_ago)})
    store.create(record)
    return record


def prune(store: InMemoryRangeStore, documents: RecordingDocuments, **input_args) -> PruneRangesOutputDto:
    boundary = RecordingBoundary()
    PruneRanges(output_boundary=boundary, store=store, documents=documents, clock=lambda: NOW).execute(
        PruneRangesInputDto(**input_args)
    )
    return boundary.presented


def test_deletes_only_ranges_destroyed_more_than_30_days_ago() -> None:
    store, documents = InMemoryRangeStore(), RecordingDocuments()
    old = add(store, RangeState.DESTROYED, 31)
    recent = add(store, RangeState.DESTROYED, 29)
    kept = [add(store, state, 90) for state in (RangeState.BUILT, RangeState.BUILD_FAILED, RangeState.DESTROY_FAILED)]

    presented = prune(store, documents)

    assert [record.id for record in presented.deleted] == [old.id]
    assert documents.deleted == [old.id]
    assert set(store.records) == {recent.id, *(record.id for record in kept)}
    assert presented.older_than == timedelta(days=30)


def test_retention_is_configurable() -> None:
    store, documents = InMemoryRangeStore(), RecordingDocuments()
    add(store, RangeState.DESTROYED, 2)

    assert len(prune(store, documents, older_than=timedelta(days=1)).deleted) == 1


def test_failure_keeps_the_record_and_goes_on() -> None:
    store = InMemoryRangeStore()
    stuck = add(store, RangeState.DESTROYED, 40)
    other = add(store, RangeState.DESTROYED, 50)

    presented = prune(store, RecordingDocuments(fail_for=stuck.id))

    assert [record.id for record in presented.deleted] == [other.id]
    assert presented.failed == {stuck.id: "read-only"}
    assert set(store.records) == {stuck.id}


@pytest.mark.parametrize("days_ago", [0, 30])
def test_nothing_to_delete(days_ago: int) -> None:
    store = InMemoryRangeStore()
    add(store, RangeState.DESTROYED, days_ago)

    presented = prune(store, RecordingDocuments())

    assert presented.deleted == [] and presented.failed == {}
    assert len(store.records) == 1

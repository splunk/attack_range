import dataclasses
from datetime import timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import pytest

from attack_range.application.cyber_range import CyberRange, CyberRangeError
from attack_range.application.provisioner import ProvisionResult, Provisioner, ProvisionerError
from attack_range.application.range_documents import RangeDocuments
from attack_range.application.repository import CyberRangeRepository
from attack_range.domain.entities.common import Provider
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState
from attack_range.use_cases.build import Build, BuildInputDto
from attack_range.use_cases.destroy import Destroy, DestroyInputDto
from attack_range.use_cases.list_ranges import (
    ListRanges,
    ListRangesInputDto,
    ListRangesOutputBoundary,
    ListRangesOutputDto,
)
from attack_range.use_cases.plan import Plan, PlanInputDto
from attack_range.use_cases.provision import ProvisionOutputBoundary, ProvisionOutputDto
from conftest import load_cyber_range
from mocks.in_memory_range_store import InMemoryRangeStore


class InMemoryRepository(CyberRangeRepository):
    def __init__(self, cyber_range: Optional[CyberRange] = None, error: str = "") -> None:
        self._cyber_range = cyber_range
        self._error = error
        self.requests: list[tuple[Path, Optional[Provider]]] = []

    def load(self, location: Path, provider: Optional[Provider] = None) -> CyberRange:
        self.requests.append((location, provider))
        if self._error:
            raise CyberRangeError(self._error)
        assert self._cyber_range is not None
        return self._cyber_range


class InMemoryDocuments(RangeDocuments):
    def __init__(self, cyber_range: CyberRange, error: str = "") -> None:
        self._cyber_range = cyber_range
        self._error = error
        self.imported: dict[UUID, Path] = {}

    def import_documents(self, range_id: UUID, source: Path) -> None:
        if self._error:
            raise ValueError(self._error)
        self.imported[range_id] = source

    def load(self, range_id: UUID, provider: Provider) -> CyberRange:
        return dataclasses.replace(self._cyber_range, id=range_id)


class RecordingProvisioner(Provisioner):
    def __init__(
        self, result: Optional[ProvisionResult] = None, error: str = "", raises: Optional[BaseException] = None
    ) -> None:
        super().__init__()
        self._result = result or ProvisionResult(success=True, output="ok", outputs={"servers": {}})
        self._error = error
        self._raises = raises
        self.calls: list[tuple[str, CyberRange]] = []

    def render(self, cyber_range: CyberRange) -> Path:
        return Path("unused")

    def _record(self, action: str, cyber_range: CyberRange) -> ProvisionResult:
        self.calls.append((action, cyber_range))
        if self._raises is not None:
            raise self._raises
        if self._error:
            raise ProvisionerError(self._error)
        return self._result

    def plan(self, cyber_range: CyberRange) -> ProvisionResult:
        return self._record("plan", cyber_range)

    def apply(self, cyber_range: CyberRange) -> ProvisionResult:
        return self._record("apply", cyber_range)

    def destroy(self, cyber_range: CyberRange) -> ProvisionResult:
        return self._record("destroy", cyber_range)

    def clean(self, cyber_range: CyberRange) -> None:
        self.calls.append(("clean", cyber_range))

    @property
    def actions(self) -> list[str]:
        return [action for action, _ in self.calls]


class RecordingBoundary(ProvisionOutputBoundary):
    def __init__(self) -> None:
        self.presented: Optional[ProvisionOutputDto] = None

    def present(self, dto: ProvisionOutputDto) -> None:
        self.presented = dto

    def get_presented_value(self) -> Optional[ProvisionOutputDto]:
        return self.presented


class RecordingListBoundary(ListRangesOutputBoundary):
    def __init__(self) -> None:
        self.presented: Optional[ListRangesOutputDto] = None

    def present(self, dto: ListRangesOutputDto) -> None:
        self.presented = dto

    def get_presented_value(self) -> Optional[ListRangesOutputDto]:
        return self.presented


@pytest.fixture
def cyber_range(ar_template_dir: Path) -> CyberRange:
    return load_cyber_range(ar_template_dir)


@pytest.fixture
def store() -> InMemoryRangeStore:
    return InMemoryRangeStore()


def build(
    cyber_range: CyberRange,
    store: InMemoryRangeStore,
    provisioner: RecordingProvisioner,
    documents: Optional[InMemoryDocuments] = None,
    local_state: bool = False,
) -> ProvisionOutputDto:
    boundary = RecordingBoundary()
    Build(
        output_boundary=boundary,
        repository=InMemoryRepository(cyber_range),
        documents=documents or InMemoryDocuments(cyber_range),
        store=store,
        provisioner=provisioner,
    ).execute(BuildInputDto(location=Path("range"), provider="aws", local_state=local_state))
    return boundary.presented


def destroy(
    cyber_range: CyberRange, store: InMemoryRangeStore, provisioner: RecordingProvisioner, range_id: UUID
) -> ProvisionOutputDto:
    boundary = RecordingBoundary()
    Destroy(
        output_boundary=boundary,
        documents=InMemoryDocuments(cyber_range),
        store=store,
        provisioner=provisioner,
    ).execute(DestroyInputDto(range_id=range_id))
    return boundary.presented


def test_plan_registers_nothing(cyber_range: CyberRange) -> None:
    boundary, repository, provisioner = RecordingBoundary(), InMemoryRepository(cyber_range), RecordingProvisioner()

    Plan(output_boundary=boundary, repository=repository, provisioner=provisioner).execute(
        PlanInputDto(location=Path("range"), provider="aws")
    )

    assert repository.requests == [(Path("range"), "aws")]
    assert provisioner.actions == ["plan"]
    assert provisioner.calls[0][1].id is None
    assert boundary.presented == ProvisionOutputDto(
        action="plan", success=True, location=Path("range"), cyber_range="ar", provider="aws", output="ok",
    )


def test_plan_presents_provisioner_error(cyber_range: CyberRange) -> None:
    boundary = RecordingBoundary()

    Plan(
        output_boundary=boundary,
        repository=InMemoryRepository(cyber_range),
        provisioner=RecordingProvisioner(error="no credentials"),
    ).execute(PlanInputDto(location=Path("range")))

    assert not boundary.presented.success
    assert boundary.presented.error == "no credentials"
    assert boundary.presented.cyber_range == "ar"


def test_build_registers_and_builds(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    provisioner = RecordingProvisioner(ProvisionResult(success=True, output="ok", outputs={"servers": {"win": {}}}))
    documents = InMemoryDocuments(cyber_range)

    presented = build(cyber_range, store, provisioner, documents, local_state=True)

    assert presented.success
    record = store.get(presented.range_id)
    assert record.state is RangeState.BUILT
    assert record.outputs == {"servers": {"win": {}}}
    assert record.local_state
    assert store.stored_states == ["created", "building", "built"]
    assert documents.imported == {record.id: Path("range")}
    applied = provisioner.calls[0][1]
    assert applied.id == record.id and applied.local_state
    assert presented.state is RangeState.BUILT
    assert presented.outputs == {"servers": {"win": {}}}


def test_each_build_gets_a_new_id(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    first = build(cyber_range, store, RecordingProvisioner())
    second = build(cyber_range, store, RecordingProvisioner())

    assert first.range_id != second.range_id
    assert len(store.list()) == 2


def test_build_with_invalid_template_registers_nothing(store: InMemoryRangeStore) -> None:
    boundary, provisioner = RecordingBoundary(), RecordingProvisioner()

    Build(
        output_boundary=boundary,
        repository=InMemoryRepository(error="bad network"),
        documents=None,
        store=store,
        provisioner=provisioner,
    ).execute(BuildInputDto(location=Path("range")))

    assert provisioner.calls == []
    assert store.list() == []
    assert not boundary.presented.success
    assert boundary.presented.error == "bad network"


def test_build_fails_when_documents_cannot_be_copied(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    provisioner = RecordingProvisioner()

    presented = build(cyber_range, store, provisioner, InMemoryDocuments(cyber_range, error="disk full"))

    assert provisioner.calls == []
    assert store.get(presented.range_id).state is RangeState.BUILD_FAILED
    assert presented.error == "disk full"


@pytest.mark.parametrize(
    ("provisioner", "error"),
    [
        (RecordingProvisioner(error="no credentials"), "no credentials"),
        (RecordingProvisioner(ProvisionResult(success=False, output="Error: boom")), "build failed"),
    ],
)
def test_failed_build_is_recorded(
    cyber_range: CyberRange, store: InMemoryRangeStore, provisioner: RecordingProvisioner, error: str
) -> None:
    presented = build(cyber_range, store, provisioner)

    assert not presented.success
    assert presented.error == error
    record = store.get(presented.range_id)
    assert record.state is RangeState.BUILD_FAILED
    assert record.error == error


def test_interrupted_build_is_recorded(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    with pytest.raises(KeyboardInterrupt):
        build(cyber_range, store, RecordingProvisioner(raises=KeyboardInterrupt()))

    [record] = store.list()
    assert record.state is RangeState.BUILD_FAILED
    assert record.error == "interrupted"


def test_destroy_keeps_record_and_cleans_code(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    range_id = build(cyber_range, store, RecordingProvisioner(), local_state=True).range_id
    provisioner = RecordingProvisioner()

    presented = destroy(cyber_range, store, provisioner, range_id)

    assert presented.success
    assert presented.state is RangeState.DESTROYED
    assert provisioner.actions == ["destroy", "clean"]
    destroyed = provisioner.calls[0][1]
    assert destroyed.id == range_id and destroyed.local_state
    record = store.get(range_id)
    assert record.state is RangeState.DESTROYED
    assert record.outputs == {}


def test_destroy_unknown_range(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    provisioner = RecordingProvisioner()

    presented = destroy(cyber_range, store, provisioner, uuid4())

    assert not presented.success
    assert "no cyber range with id" in presented.error
    assert provisioner.calls == []


def test_destroy_twice_is_refused(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    range_id = build(cyber_range, store, RecordingProvisioner()).range_id
    destroy(cyber_range, store, RecordingProvisioner(), range_id)
    provisioner = RecordingProvisioner()

    presented = destroy(cyber_range, store, provisioner, range_id)

    assert not presented.success
    assert "cannot become destroying" in presented.error
    assert presented.state is RangeState.DESTROYED
    assert provisioner.calls == []


def test_failed_destroy_can_be_retried(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    range_id = build(cyber_range, store, RecordingProvisioner()).range_id

    failed = destroy(cyber_range, store, RecordingProvisioner(ProvisionResult(success=False, output="boom")), range_id)

    assert not failed.success
    assert failed.error == "destroy failed"
    assert failed.output == "boom"
    assert store.get(range_id).state is RangeState.DESTROY_FAILED

    provisioner = RecordingProvisioner()
    assert destroy(cyber_range, store, provisioner, range_id).success
    assert provisioner.actions == ["destroy", "clean"]


def test_failed_build_can_be_destroyed(cyber_range: CyberRange, store: InMemoryRangeStore) -> None:
    range_id = build(cyber_range, store, RecordingProvisioner(error="quota")).range_id

    assert destroy(cyber_range, store, RecordingProvisioner(), range_id).success


def test_list_hides_destroyed_ranges_and_sorts_by_creation(store: InMemoryRangeStore) -> None:
    def record(name: str, age: int, state: Optional[RangeState] = None) -> RangeRecord:
        created = RangeRecord.new(name=name, provider="aws", location="eu-central-1", source="/ranges")
        created = created.model_copy(update={"created_at": created.created_at - timedelta(minutes=age)})
        if state is RangeState.DESTROYED:
            for step in (RangeState.BUILDING, RangeState.BUILT, RangeState.DESTROYING, RangeState.DESTROYED):
                created = created.transition(step)
        store.create(created)
        return created

    record("new", 1)
    record("old", 10)
    record("gone", 5, RangeState.DESTROYED)

    def listed(include_destroyed: bool) -> ListRangesOutputDto:
        boundary = RecordingListBoundary()
        ListRanges(output_boundary=boundary, store=store).execute(ListRangesInputDto(include_destroyed))
        return boundary.presented

    active = listed(False)
    assert [r.name for r in active.ranges] == ["old", "new"]
    assert active.hidden == 1
    every = listed(True)
    assert [r.name for r in every.ranges] == ["old", "gone", "new"]
    assert every.hidden == 0

from pathlib import Path
from typing import Optional, Sequence
from uuid import UUID, uuid4

import pytest

from attack_range.application.cyber_range import CyberRange, CyberRangeError, Document
from attack_range.application.range_documents import RangeDocuments
from attack_range.domain.entities.common import Provider
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState
from attack_range.use_cases.get_range import GetRange, GetRangeInputDto, GetRangeOutputBoundary, GetRangeOutputDto
from conftest import load_cyber_range
from mocks.in_memory_range_store import InMemoryRangeStore


class RecordingBoundary(GetRangeOutputBoundary):
    def __init__(self) -> None:
        self.presented: Optional[GetRangeOutputDto] = None

    def present(self, dto: GetRangeOutputDto) -> None:
        self.presented = dto

    def get_presented_value(self) -> Optional[GetRangeOutputDto]:
        return self.presented


class StoredDocuments(RangeDocuments):
    def __init__(self, cyber_range: Optional[CyberRange] = None, error: str = "") -> None:
        self._cyber_range = cyber_range
        self._error = error

    def import_documents(self, range_id: UUID, source: Path) -> None:
        raise NotImplementedError

    def paths(self, range_id: UUID) -> list[Path]:
        return []

    def load(self, range_id: UUID, provider: Provider) -> CyberRange:
        if self._error:
            raise CyberRangeError(self._error)
        assert self._cyber_range is not None
        return self._cyber_range

    def read(self, range_id: UUID) -> tuple[list[Document], dict[str, str]]:
        raise NotImplementedError

    def replace(
        self, range_id: UUID, documents: Sequence[Document], bootstrap_files: dict[str, str]
    ) -> None:
        raise NotImplementedError

    def delete(self, range_id: UUID) -> None:
        raise NotImplementedError


def _built(cyber_range: CyberRange) -> RangeRecord:
    return RangeRecord.new(
        name=cyber_range.name,
        provider=cyber_range.provider,
        location=cyber_range.location,
        source="/templates/lab",
        local_state=True,
        user_name="tester",
    ).transition(RangeState.BUILDING).transition(
        RangeState.BUILT, outputs={"servers": {"app-1": {"private_ip": "10.0.1.10", "public_ip": None}}}
    )


def test_get_returns_the_record_and_its_documents(lab_dir: Path) -> None:
    cyber_range = load_cyber_range(lab_dir, "aws")
    record = _built(cyber_range)
    store = InMemoryRangeStore()
    store.create(record)
    boundary = RecordingBoundary()

    GetRange(boundary, StoredDocuments(cyber_range), store).execute(GetRangeInputDto(range_id=record.id))

    presented = boundary.presented
    assert presented is not None and presented.success
    assert presented.record is not None and presented.record.id == record.id
    assert presented.cyber_range is not None
    assert [server.metadata.name for server in presented.cyber_range.servers] == ["app-1"]
    assert presented.documents_error is None


def test_get_reports_an_unknown_range() -> None:
    missing = uuid4()
    boundary = RecordingBoundary()

    GetRange(boundary, StoredDocuments(), InMemoryRangeStore()).execute(GetRangeInputDto(range_id=missing))

    presented = boundary.presented
    assert presented is not None and not presented.success
    assert presented.record is None
    assert str(missing) in (presented.error or "")


def test_get_prints_the_wireguard_endpoint(lab_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from cli.presenter import CliGetPresenter

    record = _built(load_cyber_range(lab_dir, "aws")).model_copy(update={"outputs": {
        "wireguard": {"public_ip": "203.0.113.10", "client_config": "/ranges/id/wireguard/client.conf"},
    }})

    CliGetPresenter().present(GetRangeOutputDto(success=True, range_id=record.id, record=record))

    out = capsys.readouterr().out
    assert "203.0.113.10:51820" in out
    assert "/ranges/id/wireguard/client.conf" in out


def test_get_lists_the_config_files(lab_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from cli.presenter import CliGetPresenter

    record = _built(load_cyber_range(lab_dir, "aws"))
    root = Path("/ranges/id/documents")
    files = (
        root / "lab.network.yaml",
        root / "app-1.server.yaml",
        root / "app-1.server-binding.aws.yaml",
        root / "user-data" / "app-1.ps1",
    )

    CliGetPresenter().present(GetRangeOutputDto(
        success=True, range_id=record.id, record=record, files=files,
    ))

    out = capsys.readouterr().out
    assert f"files  {root}" in out
    assert "lab.network.yaml" in out
    assert "app-1.server.yaml" in out
    assert "app-1.server-binding.aws.yaml" in out
    assert "user-data/app-1.ps1" in out


def test_get_keeps_the_record_when_documents_cannot_be_read(lab_dir: Path) -> None:
    cyber_range = load_cyber_range(lab_dir, "aws")
    record = _built(cyber_range)
    store = InMemoryRangeStore()
    store.create(record)
    boundary = RecordingBoundary()

    GetRange(boundary, StoredDocuments(error="unreadable"), store).execute(GetRangeInputDto(range_id=record.id))

    presented = boundary.presented
    assert presented is not None and presented.success
    assert presented.record is not None and presented.record.id == record.id
    assert presented.cyber_range is None
    assert presented.documents_error == "unreadable"

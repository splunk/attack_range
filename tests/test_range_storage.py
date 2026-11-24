from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from attack_range.application.cyber_range import CyberRangeError
from attack_range.application.range_store import RangeNotFound
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState
from attack_range_infrastructure.storage import (
    AttackRangeHome,
    FileCyberRangeRepository,
    FileRangeDocuments,
    YamlRangeStore,
)


def new_record(name: str = "ar") -> RangeRecord:
    return RangeRecord.new(name=name, provider="aws", location="eu-central-1", source="/ranges/ar")


def test_home_defaults_to_environment(home_root: Path) -> None:
    home = AttackRangeHome().ensure()

    assert home.root == home_root
    assert home.ranges_dir.is_dir() and home.plans_dir.is_dir()


def test_home_defaults_to_user_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ATTACK_RANGE_HOME")

    assert AttackRangeHome().root == Path.home() / ".attack_range"


def test_store_round_trip(home: AttackRangeHome) -> None:
    store = YamlRangeStore(home)
    record = new_record()

    store.create(record)
    built = record.transition(RangeState.BUILDING).transition(RangeState.BUILT, outputs={"servers": {"win": {}}})
    store.update(built)

    assert store.get(record.id) == built
    stored = yaml.safe_load(home.record_file(record.id).read_text())
    assert stored["state"] == "built"
    assert stored["id"] == str(record.id)


def test_store_create_refuses_existing_id(home: AttackRangeHome) -> None:
    store = YamlRangeStore(home)
    record = new_record()
    store.create(record)

    with pytest.raises(ValueError, match="already exists"):
        store.create(record)


def test_store_unknown_id(home: AttackRangeHome) -> None:
    store = YamlRangeStore(home)

    with pytest.raises(RangeNotFound):
        store.get(uuid4())
    with pytest.raises(RangeNotFound):
        store.update(new_record())


def test_list_skips_a_record_this_version_cannot_read(home: AttackRangeHome) -> None:
    store = YamlRangeStore(home)
    record = new_record()
    store.create(record)
    leftover = home.ranges_dir / "2bf475f0-5bb7-45aa-9c9a-1174a161a6ec"
    leftover.mkdir()
    (leftover / "range.yaml").write_text(
        "id: 2bf475f0-5bb7-45aa-9c9a-1174a161a6ec\nprovider: fusion\n"
    )

    assert [item.id for item in store.list()] == [record.id]
    with pytest.raises(ValueError, match="not a valid range record"):
        store.get(UUID("2bf475f0-5bb7-45aa-9c9a-1174a161a6ec"))


def test_store_lists_ranges_and_skips_other_folders(home: AttackRangeHome) -> None:
    store = YamlRangeStore(home)
    first, second = new_record("one"), new_record("two")
    store.create(first)
    store.create(second)
    (home.ranges_dir / "notes").mkdir()

    assert sorted(record.name for record in store.list()) == ["one", "two"]


def test_delete_removes_the_range_folder(home: AttackRangeHome, ar_template_dir: Path) -> None:
    store = YamlRangeStore(home)
    documents = FileRangeDocuments(home, FileCyberRangeRepository())
    record = new_record()
    store.create(record)
    documents.import_documents(record.id, ar_template_dir)

    documents.delete(record.id)
    documents.delete(record.id)
    store.delete(record.id)

    assert not home.range_dir(record.id).exists()
    assert store.list() == []
    with pytest.raises(RangeNotFound):
        store.delete(record.id)


def test_delete_keeps_folder_with_other_files(home: AttackRangeHome) -> None:
    store = YamlRangeStore(home)
    record = new_record()
    store.create(record)
    (home.range_dir(record.id) / "notes.txt").write_text("keep")

    store.delete(record.id)

    assert (home.range_dir(record.id) / "notes.txt").is_file()
    assert store.list() == []


def test_import_copies_documents_and_user_data(home: AttackRangeHome, lab_dir: Path) -> None:
    (lab_dir / "README.txt").write_text("not a document")
    documents = FileRangeDocuments(home, FileCyberRangeRepository())
    range_id = uuid4()

    documents.import_documents(range_id, lab_dir)

    target = home.documents_dir(range_id)
    assert sorted(path.name for path in target.glob("*.yaml")) == sorted(path.name for path in lab_dir.glob("*.yaml"))
    assert (target / "user-data" / "app-1.ps1").is_file()
    assert not (target / "README.txt").exists()
    cyber_range = documents.load(range_id, "vmware")
    assert cyber_range.id == range_id
    assert cyber_range.name == "lab"


def test_copy_does_not_follow_later_template_changes(home: AttackRangeHome, lab_dir: Path) -> None:
    documents = FileRangeDocuments(home, FileCyberRangeRepository())
    range_id = uuid4()
    documents.import_documents(range_id, lab_dir)

    (lab_dir / "lab.network-binding.aws.yaml").unlink()

    assert documents.load(range_id, "aws").provider == "aws"


def test_import_refuses_existing_documents(home: AttackRangeHome, ar_template_dir: Path) -> None:
    documents = FileRangeDocuments(home, FileCyberRangeRepository())
    range_id = uuid4()
    documents.import_documents(range_id, ar_template_dir)

    with pytest.raises(ValueError, match="already has documents"):
        documents.import_documents(range_id, ar_template_dir)


def test_load_without_documents(home: AttackRangeHome) -> None:
    with pytest.raises(CyberRangeError, match="has no documents"):
        FileRangeDocuments(home, FileCyberRangeRepository()).load(uuid4(), "aws")


def test_template_can_be_a_single_file(tmp_path: Path, ar_template_dir: Path) -> None:
    combined = tmp_path / "ar.yaml"
    combined.write_text("\n---\n".join(path.read_text() for path in sorted(ar_template_dir.glob("*.yaml"))))

    cyber_range = FileCyberRangeRepository().load(combined)

    assert cyber_range.name == "ar"
    assert sorted(server.metadata.name for server in cyber_range.servers) == ["splunk", "win"]

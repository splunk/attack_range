from pathlib import Path
from uuid import uuid4

import yaml

from attack_range.application.cyber_range import CyberRangeError
from attack_range.application.provisioner import ProvisionResult, Provisioner
from attack_range.domain.entities import parse_document
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState
from attack_range.use_cases.provision import ConfigChange, ProvisionOutputBoundary, ProvisionOutputDto
from attack_range.use_cases.update import (
    Update,
    UpdateInputDto,
    _with_bootstrap_changes,
    classify,
    servers_to_provision,
)
from attack_range_infrastructure.storage import (
    AttackRangeHome,
    FileCyberRangeRepository,
    FileRangeDocuments,
    YamlRangeStore,
)
from conftest import load_cyber_range


class RecordingBoundary(ProvisionOutputBoundary):
    def __init__(self) -> None:
        self.presented: ProvisionOutputDto | None = None

    def present(self, dto: ProvisionOutputDto) -> None:
        self.presented = dto

    def get_presented_value(self) -> ProvisionOutputDto | None:
        return self.presented


class RecordingProvisioner(Provisioner):
    def __init__(self) -> None:
        super().__init__()
        self.applied = 0

    def render(self, cyber_range) -> Path:
        return Path("unused")

    def plan(self, cyber_range):
        raise AssertionError("update does not plan")

    def apply(self, cyber_range):
        self.applied += 1
        return ProvisionResult(success=True, output="applied", outputs={"servers": {}})

    def destroy(self, cyber_range):
        raise AssertionError("update does not destroy")

    def clean(self, cyber_range) -> None:
        raise AssertionError("update does not clean")


def _binding(path: Path, instance_type: str | None = None, name: str | None = None):
    data = yaml.safe_load(path.read_text())
    if instance_type is not None:
        data["spec"]["aws"]["instanceType"] = instance_type
    if name is not None:
        data["metadata"]["name"] = name
    return parse_document(data)


def test_classify_tells_a_parameter_change_from_a_new_document(lab_dir: Path) -> None:
    binding = lab_dir / "lab.server-binding.aws.yaml"
    current = _binding(binding)
    modified = _binding(binding, instance_type="t3.large")
    added = _binding(binding, name="extra-aws")

    changes = classify([current], [modified, added])

    assert [(change.action, change.name, change.parameters) for change in changes] == [
        ("modified", "app-1-aws", ("spec.aws.instanceType",)),
        ("added", "extra-aws", ()),
    ]
    assert classify([current], [current]) == []


def test_only_added_or_modified_servers_are_provisioned(lab_dir: Path) -> None:
    cyber_range = load_cyber_range(lab_dir, "aws")
    changes = [
        ConfigChange(kind="ServerBinding", name="app-1-aws", action="modified", parameters=("spec.aws.instanceType",)),
        ConfigChange(kind="Network", name="lab", action="modified", parameters=("spec.addressSpace",)),
        ConfigChange(kind="Server", name="win", action="added"),
    ]

    assert servers_to_provision(changes, cyber_range) == {"app-1", "win"}
    assert servers_to_provision(
        [ConfigChange(kind="Server", name="app-1", action="removed")], cyber_range
    ) == set()


def test_a_changed_bootstrap_script_is_a_server_change(lab_dir: Path) -> None:
    server = parse_document(yaml.safe_load((lab_dir / "lab.server.yaml").read_text()))

    changes = _with_bootstrap_changes([], [server], {"app-1.ps1": "old\n"}, {"app-1.ps1": "new\n"})

    assert [(change.action, change.name, change.parameters) for change in changes] == [
        ("modified", "app-1", ("bootstrap.userData",)),
    ]
    assert _with_bootstrap_changes([], [server], {"app-1.ps1": "same\n"}, {"app-1.ps1": "same\n"}) == []
    assert _with_bootstrap_changes(
        [ConfigChange(kind="Server", name="app-1", action="modified")],
        [server],
        {"app-1.ps1": "old\n"},
        {"app-1.ps1": "new\n"},
    ) == [ConfigChange(kind="Server", name="app-1", action="modified")]


def test_classify_rejects_the_same_document_twice(lab_dir: Path) -> None:
    current = _binding(lab_dir / "lab.server-binding.aws.yaml")

    try:
        classify([current], [current, current])
    except CyberRangeError as error:
        assert "duplicate ServerBinding 'app-1-aws'" in str(error)
    else:
        raise AssertionError("expected a duplicate document to be rejected")


def test_update_applies_a_changed_parameter_and_keeps_the_rest(home: AttackRangeHome, lab_dir: Path, tmp_path: Path) -> None:
    cyber_range = load_cyber_range(lab_dir, "aws")
    record = RangeRecord.new(
        name=cyber_range.name,
        provider="aws",
        location=cyber_range.location,
        source=str(lab_dir),
        local_state=True,
        user_name="tester",
    ).transition(RangeState.BUILDING).transition(RangeState.BUILT)
    store = YamlRangeStore(home)
    store.create(record)
    documents = FileRangeDocuments(home, FileCyberRangeRepository())
    documents.import_documents(record.id, lab_dir)
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    text = (lab_dir / "lab.server-binding.aws.yaml").read_text().replace("t3.micro", "t3.large")
    (overlay / "lab.server-binding.aws.yaml").write_text(text)
    boundary = RecordingBoundary()
    provisioner = RecordingProvisioner()

    Update(boundary, FileCyberRangeRepository(), documents, store, provisioner).execute(
        UpdateInputDto(range_id=record.id, location=overlay)
    )

    presented = boundary.presented
    assert presented is not None and presented.success
    assert presented.action == "update"
    assert [(change.action, change.kind, change.name, change.parameters) for change in presented.changes] == [
        ("modified", "ServerBinding", "app-1-aws", ("spec.aws.instanceType",)),
    ]
    assert provisioner.applied == 1
    assert store.get(record.id).state is RangeState.BUILT
    assert store.get(record.id).source == str(lab_dir)
    reloaded = documents.load(record.id, "aws")
    assert reloaded.server_bindings["app-1"].spec.aws is not None
    assert reloaded.server_bindings["app-1"].spec.aws.instance_type == "t3.large"
    stored, files = documents.read(record.id)
    identities = {(document.kind, document.metadata.name) for document in stored}
    assert ("Network", "lab") in identities
    assert ("NetworkBinding", "lab-azure") in identities
    assert ("Server", "app-1") in identities
    assert files["app-1.ps1"].startswith("Write-Host")


def test_unchanged_documents_skip_terraform(home: AttackRangeHome, lab_dir: Path) -> None:
    cyber_range = load_cyber_range(lab_dir, "aws")
    record = RangeRecord.new(
        name=cyber_range.name, provider="aws", location=cyber_range.location,
        source=str(lab_dir), user_name="tester",
    ).transition(RangeState.BUILDING).transition(RangeState.BUILT)
    store = YamlRangeStore(home)
    store.create(record)
    documents = FileRangeDocuments(home, FileCyberRangeRepository())
    documents.import_documents(record.id, lab_dir)
    boundary = RecordingBoundary()
    provisioner = RecordingProvisioner()

    Update(boundary, FileCyberRangeRepository(), documents, store, provisioner).execute(
        UpdateInputDto(range_id=record.id, location=lab_dir / "lab.server-binding.aws.yaml")
    )

    assert boundary.presented is not None and boundary.presented.success
    assert boundary.presented.changes == ()
    assert provisioner.applied == 0
    assert store.get(record.id).state is RangeState.BUILT


def _stored_range(home: AttackRangeHome, lab_dir: Path):
    cyber_range = load_cyber_range(lab_dir, "aws")
    record = RangeRecord.new(
        name=cyber_range.name, provider="aws", location=cyber_range.location,
        source=str(lab_dir), user_name="tester",
    ).transition(RangeState.BUILDING).transition(RangeState.BUILT)
    store = YamlRangeStore(home)
    store.create(record)
    documents = FileRangeDocuments(home, FileCyberRangeRepository())
    documents.import_documents(record.id, lab_dir)
    return record, documents, store


def test_change_applies_a_modified_file(home: AttackRangeHome, lab_dir: Path, tmp_path: Path) -> None:
    record, documents, store = _stored_range(home, lab_dir)
    changed = tmp_path / "lab.server-binding.aws.yaml"
    changed.write_text((lab_dir / "lab.server-binding.aws.yaml").read_text().replace("t3.micro", "t3.large"))
    boundary = RecordingBoundary()
    provisioner = RecordingProvisioner()

    Update(boundary, FileCyberRangeRepository(), documents, store, provisioner).execute(
        UpdateInputDto(range_id=record.id, location=changed, mode="change")
    )

    presented = boundary.presented
    assert presented is not None and presented.success
    assert [(change.action, change.kind, change.name) for change in presented.changes] == [
        ("modified", "ServerBinding", "app-1-aws"),
    ]
    assert provisioner.applied == 1
    reloaded = documents.load(record.id, "aws")
    assert reloaded.server_bindings["app-1"].spec.aws is not None
    assert reloaded.server_bindings["app-1"].spec.aws.instance_type == "t3.large"


def test_change_rejects_a_new_document(home: AttackRangeHome, lab_dir: Path, tmp_path: Path) -> None:
    record, documents, store = _stored_range(home, lab_dir)
    added = tmp_path / "extra.server-binding.aws.yaml"
    text = (lab_dir / "lab.server-binding.aws.yaml").read_text().replace("name: app-1-aws", "name: extra-aws")
    added.write_text(text.replace("server: app-1", "server: extra"))
    boundary = RecordingBoundary()
    provisioner = RecordingProvisioner()

    Update(boundary, FileCyberRangeRepository(), documents, store, provisioner).execute(
        UpdateInputDto(range_id=record.id, location=added, mode="change")
    )

    presented = boundary.presented
    assert presented is not None and not presented.success
    assert "ServerBinding 'extra-aws' is not in the range" in (presented.error or "")
    assert provisioner.applied == 0


def test_change_accepts_a_folder_of_existing_documents(home: AttackRangeHome, lab_dir: Path, tmp_path: Path) -> None:
    record, documents, store = _stored_range(home, lab_dir)
    folder = tmp_path / "changed"
    folder.mkdir()
    text = (lab_dir / "lab.server.yaml").read_text().replace("username: ubuntu", "username: admin")
    (folder / "lab.server.yaml").write_text(text)
    boundary = RecordingBoundary()
    provisioner = RecordingProvisioner()

    Update(boundary, FileCyberRangeRepository(), documents, store, provisioner).execute(
        UpdateInputDto(range_id=record.id, location=folder, mode="change")
    )

    presented = boundary.presented
    assert presented is not None and presented.success
    assert [(change.action, change.kind, change.name) for change in presented.changes] == [
        ("modified", "Server", "app-1"),
    ]
    assert documents.load(record.id, "aws").servers[0].spec.access.username == "admin"


def test_remove_drops_a_server_with_its_binding(home: AttackRangeHome, lab_dir: Path) -> None:
    record, documents, store = _stored_range(home, lab_dir)
    boundary = RecordingBoundary()
    provisioner = RecordingProvisioner()

    Update(boundary, FileCyberRangeRepository(), documents, store, provisioner).execute(
        UpdateInputDto(range_id=record.id, files=("lab.server.yaml", "lab.server-binding.aws.yaml"))
    )

    presented = boundary.presented
    assert presented is not None and presented.success
    assert {(change.action, change.kind, change.name) for change in presented.changes} == {
        ("removed", "Server", "app-1"),
        ("removed", "ServerBinding", "app-1-aws"),
    }
    assert provisioner.applied == 1
    assert documents.load(record.id, "aws").servers == []
    assert all(path.name != "app-1.ps1" for path in documents.paths(record.id))


def test_remove_rejects_a_binding_without_its_server(home: AttackRangeHome, lab_dir: Path) -> None:
    record, documents, store = _stored_range(home, lab_dir)
    boundary = RecordingBoundary()
    provisioner = RecordingProvisioner()

    Update(boundary, FileCyberRangeRepository(), documents, store, provisioner).execute(
        UpdateInputDto(range_id=record.id, files=("lab.server-binding.aws.yaml",))
    )

    presented = boundary.presented
    assert presented is not None and not presented.success
    assert "server binding 'app-1-aws' cannot be removed without server 'app-1'" in (presented.error or "")
    assert provisioner.applied == 0
    assert [server.metadata.name for server in documents.load(record.id, "aws").servers] == ["app-1"]


def test_remove_rejects_a_server_without_its_binding(home: AttackRangeHome, lab_dir: Path) -> None:
    record, documents, store = _stored_range(home, lab_dir)
    boundary = RecordingBoundary()

    Update(boundary, FileCyberRangeRepository(), documents, store, RecordingProvisioner()).execute(
        UpdateInputDto(range_id=record.id, files=("lab.server.yaml",))
    )

    presented = boundary.presented
    assert presented is not None and not presented.success
    assert "server 'app-1' cannot be removed without server binding 'app-1-aws'" in (presented.error or "")


def test_remove_rejects_an_unknown_config_file(home: AttackRangeHome, lab_dir: Path) -> None:
    record, documents, store = _stored_range(home, lab_dir)
    boundary = RecordingBoundary()

    Update(boundary, FileCyberRangeRepository(), documents, store, RecordingProvisioner()).execute(
        UpdateInputDto(range_id=record.id, files=("missing.yaml",))
    )

    presented = boundary.presented
    assert presented is not None and not presented.success
    assert "config file 'missing.yaml' is not in the range" in (presented.error or "")


def test_unknown_range_is_reported(home: AttackRangeHome, tmp_path: Path) -> None:
    boundary = RecordingBoundary()
    missing = uuid4()

    Update(
        boundary, FileCyberRangeRepository(), FileRangeDocuments(home, FileCyberRangeRepository()),
        YamlRangeStore(home), RecordingProvisioner(),
    ).execute(UpdateInputDto(range_id=missing, location=tmp_path))

    assert boundary.presented is not None and not boundary.presented.success
    assert str(missing) in (boundary.presented.error or "")

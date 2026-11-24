from pathlib import Path

import pytest

from attack_range.application.cyber_range import CyberRangeError
from attack_range.application.overrides import DeployOverrides, FieldOverride, override_documents, override_range
from attack_range.use_cases.build import Build
from attack_range_infrastructure.storage.file_cyber_range_repository import FileCyberRangeRepository
from cli.main import main
from conftest import REPO

LAB = REPO / "templates" / "azure" / "ar_cisco_lab"
IMAGE = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/images-e6fffcb8-tester/providers/Microsoft.Compute/images/ftd"


def test_set_replaces_one_document_field() -> None:
    loaded = FileCyberRangeRepository().load(LAB, "azure")
    updated = override_range(loaded, DeployOverrides(sets=(
        FieldOverride("ftd-azure", ("spec", "azure", "imageId"), IMAGE),
    )))
    ftd = next(server for server in updated.servers if server.metadata.name == "ftd")

    assert updated.binding(ftd).spec.azure.image_id == IMAGE


def test_star_sets_only_documents_of_the_provider(lab_dir: Path) -> None:
    documents, _files = FileCyberRangeRepository().read(lab_dir)
    updated = override_documents(documents, "aws", DeployOverrides(sets=(
        FieldOverride("*", ("spec", "location"), "eu-west-1"),
    )))
    aws = next(document for document in updated if document.metadata.name == "lab-aws")
    azure = next(document for document in updated if document.metadata.name == "lab-azure")

    assert aws.spec.location == "eu-west-1"
    assert azure.spec.location == "westeurope"


def test_set_rejects_an_unknown_document(lab_dir: Path) -> None:
    documents, _files = FileCyberRangeRepository().read(lab_dir)

    with pytest.raises(CyberRangeError, match="no document 'missing' has spec.location"):
        override_documents(documents, "aws", DeployOverrides(sets=(
            FieldOverride("missing", ("spec", "location"), "eu-west-1"),
        )))


def test_build_accepts_set(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def execute(self, input_dto) -> None:
        captured["sets"] = input_dto.sets

    monkeypatch.setattr(Build, "execute", execute)

    with pytest.raises(SystemExit):
        main(["build", "unused", "--set", f"ftd-azure.spec.azure.imageId={IMAGE}"])

    assert captured["sets"] == (FieldOverride("ftd-azure", ("spec", "azure", "imageId"), IMAGE),)

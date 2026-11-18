from pathlib import Path

import pytest

from attack_range.application.cyber_range import CyberRangeError
from conftest import edit, load_cyber_range


def test_loads_ar_template(ar_template_dir: Path) -> None:
    cyber_range = load_cyber_range(ar_template_dir, "aws")

    assert cyber_range.name == "ar"
    assert cyber_range.provider == "aws"
    assert cyber_range.location == "eu-central-1"
    assert sorted(server.metadata.name for server in cyber_range.servers) == ["splunk", "win"]
    assert set(cyber_range.server_bindings) == {"splunk", "win"}


@pytest.mark.parametrize("provider", ["aws", "azure", "vmware"])
def test_selects_bindings_of_provider(lab_dir: Path, provider: str) -> None:
    cyber_range = load_cyber_range(lab_dir, provider)

    assert cyber_range.network_binding.spec.provider == provider
    assert cyber_range.binding(cyber_range.servers[0]).spec.provider == provider
    assert cyber_range.user_data(cyber_range.servers[0]).startswith("Write-Host")


def test_infers_the_only_provider(ar_template_dir: Path) -> None:
    assert load_cyber_range(ar_template_dir).provider == "aws"


def test_needs_provider_when_several_are_bound(lab_dir: Path) -> None:
    with pytest.raises(CyberRangeError, match="choose a provider; the NetworkBindings name aws, azure, vmware"):
        load_cyber_range(lab_dir)


def test_missing_user_data(lab_dir: Path) -> None:
    (lab_dir / "user-data" / "app-1.ps1").unlink()

    with pytest.raises(CyberRangeError, match="user data 'app-1.ps1' is missing"):
        load_cyber_range(lab_dir, "aws")


def test_missing_location(tmp_path: Path) -> None:
    with pytest.raises(CyberRangeError, match="is neither a file nor a directory"):
        load_cyber_range(tmp_path / "missing", "aws")


def test_missing_server_binding(lab_dir: Path) -> None:
    (lab_dir / "lab.server-binding.aws.yaml").unlink()

    with pytest.raises(CyberRangeError, match="has no aws ServerBinding"):
        load_cyber_range(lab_dir, "aws")


def test_missing_network_binding(lab_dir: Path) -> None:
    (lab_dir / "lab.network-binding.azure.yaml").unlink()

    with pytest.raises(CyberRangeError, match="NetworkBinding"):
        load_cyber_range(lab_dir, "azure")


def test_unknown_segment(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server.yaml", "segment: subnet-2", "segment: subnet-9")

    with pytest.raises(CyberRangeError, match="unknown segment 'subnet-9'"):
        load_cyber_range(lab_dir, "aws")


def test_address_outside_segment(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server.yaml", "address: 10.0.1.10", "address: 10.0.0.10")

    with pytest.raises(CyberRangeError, match="outside segment"):
        load_cyber_range(lab_dir, "aws")


def test_location_mismatch(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server-binding.aws.yaml", "location: eu-central-1", "location: us-east-1")

    with pytest.raises(CyberRangeError, match="differs from network binding location"):
        load_cyber_range(lab_dir, "aws")


def test_invalid_document(lab_dir: Path) -> None:
    edit(lab_dir / "lab.network.yaml", "exposure: private", "exposure: secret")

    with pytest.raises(CyberRangeError, match="lab.network.yaml"):
        load_cyber_range(lab_dir, "aws")

from pathlib import Path

import pytest
import yaml

from attack_range.application.cyber_range import CyberRangeError
from attack_range_infrastructure.terraform.renderers import AwsRenderer, AzureRenderer
from conftest import RESOURCE_PREFIX, RESOURCE_USER, identified, load_cyber_range

TAGS = {"splunkit_environment_type": "non-prd", "splunkit_data_classification": "private"}

UNTAGGED_AZURE = {
    "azurerm_subnet",
    "azurerm_network_security_rule",
    "azurerm_subnet_network_security_group_association",
    "azurerm_subnet_nat_gateway_association",
    "azurerm_nat_gateway_public_ip_association",
    "azurerm_network_interface_security_group_association",
}


def set_tags(binding: Path, tags: object) -> None:
    document = yaml.safe_load(binding.read_text())
    if tags is None:
        document["spec"].pop("tags", None)
    else:
        document["spec"]["tags"] = tags
    binding.write_text(yaml.safe_dump(document, sort_keys=False))


def test_binding_tags_reach_the_cyber_range(lab_dir: Path) -> None:
    assert load_cyber_range(lab_dir, "aws").tags == TAGS
    assert load_cyber_range(lab_dir, "vmware").tags == {}


@pytest.mark.parametrize(
    ("tags", "message"),
    [
        ({"": "x"}, "at least 1 character"),
        ({"k" * 129: "x"}, "at most 128 characters"),
        ({"owner": "v" * 257}, "at most 256 characters"),
        ({"aws:createdBy": "me"}, "reserved by the cloud provider"),
        ({"azure-team": "me"}, "reserved by the cloud provider"),
        ({"cost/center": "42"}, "contains /"),
        ({"a<b": "x"}, "contains <"),
        ({"Name": "mine"}, "is set by attack range"),
        ({"attack-range": "mine"}, "is set by attack range"),
    ],
)
def test_invalid_tags_are_rejected(lab_dir: Path, tags: dict, message: str) -> None:
    set_tags(lab_dir / "lab.network-binding.aws.yaml", tags)

    with pytest.raises(CyberRangeError, match=message):
        load_cyber_range(lab_dir, "aws")


def test_vmware_rejects_tags(lab_dir: Path) -> None:
    set_tags(lab_dir / "lab.network-binding.vmware.yaml", TAGS)

    with pytest.raises(CyberRangeError, match="VMware bindings do not support tags"):
        load_cyber_range(lab_dir, "vmware")


def test_aws_uses_provider_default_tags(lab_dir: Path) -> None:
    doc = AwsRenderer().render(identified(load_cyber_range(lab_dir, "aws")))

    assert doc["provider"]["aws"] == {"region": "eu-central-1", "default_tags": {"tags": TAGS}}
    assert doc["resource"]["aws_vpc"]["vpc"]["tags"] == {
        "Name": f"vpc-{RESOURCE_PREFIX}-{RESOURCE_USER}",
        "attack-range": "lab",
    }


def test_aws_without_tags_has_no_default_tags(lab_dir: Path) -> None:
    set_tags(lab_dir / "lab.network-binding.aws.yaml", None)

    assert AwsRenderer().render(identified(load_cyber_range(lab_dir, "aws")))["provider"]["aws"] == {
        "region": "eu-central-1"
    }


def test_azure_tags_every_taggable_resource(lab_dir: Path) -> None:
    resources = AzureRenderer().render(identified(load_cyber_range(lab_dir, "azure")))["resource"]

    tagged = {kind for kind in resources if kind not in UNTAGGED_AZURE}
    assert {"azurerm_resource_group", "azurerm_public_ip", "azurerm_nat_gateway",
            "azurerm_network_security_group", "azurerm_network_interface"} <= tagged
    for kind in tagged:
        for name, body in resources[kind].items():
            assert body["tags"] == {**TAGS, "attack-range": "lab"}, f"{kind}.{name}"

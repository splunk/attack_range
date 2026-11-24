import dataclasses
from pathlib import Path

import pytest

from attack_range.application.cyber_range import CyberRangeError
from attack_range_infrastructure.terraform.renderers import AwsRenderer, RenderError
from attack_range_infrastructure.terraform.wireguard import listen_port, load_gateway
from conftest import RESOURCE_PREFIX, RESOURCE_USER, edit, identified, load_cyber_range


def render(path: Path) -> dict:
    return AwsRenderer().render(identified(load_cyber_range(path, "aws")))


def test_ami_name_filter_selects_the_newest_image(ar_template_dir: Path) -> None:
    doc = render(ar_template_dir)

    assert doc["data"]["aws_ami"]["win"] == {
        "most_recent": True,
        "owners": ["801119661308"],
        "filter": [{"name": "name", "values": ["Windows_Server-2022-English-Full-Base-*"]}],
    }
    assert doc["resource"]["aws_instance"]["win"]["ami"] == "${data.aws_ami.win.id}"
    assert doc["resource"]["aws_instance"]["splunk"]["ami"] == "ami-0c7377abade72a956"


def test_ami_filter_needs_its_owner(lab_dir: Path) -> None:
    edit(
        lab_dir / "lab.server-binding.aws.yaml",
        "    ami: ami-0123456789abcdef0\n",
        "    ami_name_filter: ubuntu-*\n",
    )

    with pytest.raises(CyberRangeError, match="amiNameFilter and amiOwner are set together"):
        load_cyber_range(lab_dir, "aws")


def test_ami_and_filter_together_are_rejected(lab_dir: Path) -> None:
    edit(
        lab_dir / "lab.server-binding.aws.yaml",
        "    ami: ami-0123456789abcdef0\n",
        "    ami: ami-0123456789abcdef0\n    ami_owner: 801119661308\n    ami_name_filter: Windows_*\n",
    )

    with pytest.raises(CyberRangeError, match="either ami or amiNameFilter"):
        load_cyber_range(lab_dir, "aws")


def test_subnet_zone_is_the_first_zone_of_the_region(lab_dir: Path) -> None:
    doc = render(lab_dir)

    assert doc["provider"]["aws"]["region"] == "eu-central-1"
    assert doc["resource"]["aws_subnet"]["subnet_1"]["availability_zone"] == "eu-central-1a"
    assert doc["resource"]["aws_subnet"]["subnet_2"]["availability_zone"] == "eu-central-1a"


def test_network(ar_template_dir: Path) -> None:
    doc = render(ar_template_dir)
    resources = doc["resource"]

    region = doc["provider"]["aws"]["region"]
    assert region == "eu-central-1"
    assert resources["aws_vpc"]["vpc"]["cidr_block"] == "10.0.0.0/16"
    assert resources["aws_subnet"]["mgmt"]["cidr_block"] == "10.0.2.0/24"
    assert resources["aws_subnet"]["mgmt"]["availability_zone"] == f"{region}a"
    assert resources["aws_nat_gateway"]["egress"]["subnet_id"] == "${aws_subnet.public.id}"


def test_routing(ar_template_dir: Path) -> None:
    routes = render(ar_template_dir)["resource"]["aws_route"]

    assert routes["public_internet"]["gateway_id"] == "${aws_internet_gateway.igw.id}"
    assert routes["mgmt_internet"]["nat_gateway_id"] == "${aws_nat_gateway.egress.id}"


def test_filters_and_perimeter(lab_dir: Path) -> None:
    resources = render(lab_dir)["resource"]

    assert resources["aws_security_group"]["ssh"]["name"] == f"ssh-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    ingress = resources["aws_vpc_security_group_ingress_rule"]["ssh_0_0_0"]
    assert ingress == {
        "security_group_id": "${aws_security_group.ssh.id}",
        "cidr_ipv4": "0.0.0.0/0",
        "ip_protocol": "tcp",
        "from_port": 22,
        "to_port": 22,
    }
    egress = resources["aws_vpc_security_group_egress_rule"]["ssh_1_0_0"]
    assert egress["ip_protocol"] == "-1" and "from_port" not in egress

    acl = resources["aws_network_acl"]["perimeter"]
    assert acl["subnet_ids"] == ["${aws_subnet.subnet_1.id}"]
    cidrs = [rule["cidr_block"] for rule in resources["aws_network_acl_rule"].values() if not rule["egress"]]
    assert cidrs[:2] == ["203.0.113.10/32", "10.0.0.0/16"]


def test_generated_public_key_is_the_server_key(lab_dir: Path) -> None:
    public = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKeyForTheRange"
    cyber_range = dataclasses.replace(identified(load_cyber_range(lab_dir, "aws")), ssh_public_key=public)

    doc = AwsRenderer().render(cyber_range)

    pair = doc["resource"]["aws_key_pair"]["range"]
    assert pair["key_name"] == f"key-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    assert pair["public_key"] == public
    assert doc["resource"]["aws_instance"]["app_1"]["key_name"] == "${aws_key_pair.range.key_name}"


def test_server_without_a_generated_key_uses_key_name(lab_dir: Path) -> None:
    assert render(lab_dir)["resource"]["aws_instance"]["app_1"]["key_name"] == "lab"


def test_wireguard_gateway_is_added_without_a_template_server(lab_dir: Path) -> None:
    doc = render(lab_dir)
    resources = doc["resource"]

    instance = resources["aws_instance"]["wireguard"]
    _, binding = load_gateway("aws")
    settings = binding.spec.aws
    assert instance["instance_type"] == settings.instance_type
    assert instance["ami"] == "${data.aws_ami.wireguard.id}"
    assert instance["root_block_device"] == {
        "volume_size": settings.root_volume.size_gib,
        "volume_type": settings.root_volume.type,
    }
    assert "user_data" not in instance
    assert instance["depends_on"] == ["aws_eip.wireguard"]
    assert resources["aws_eip"]["wireguard"]["network_interface"] == "${aws_network_interface.wireguard.id}"
    assert resources["aws_network_interface"]["wireguard"]["subnet_id"] == "${aws_subnet.subnet_1.id}"
    ingress = resources["aws_vpc_security_group_ingress_rule"]["wireguard_udp_0"]
    assert ingress["ip_protocol"] == "udp" and ingress["from_port"] == listen_port(load_gateway("aws")[0])
    assert ingress["cidr_ipv4"] == "203.0.113.10/32"
    assert "wireguard" not in doc["output"]["servers"]["value"]
    assert doc["output"]["wireguard"]["value"]["public_ip"] == "${aws_eip.wireguard.public_ip}"


def test_wireguard_needs_an_internet_gateway(lab_dir: Path) -> None:
    network = lab_dir / "lab.network.yaml"
    text = network.read_text()
    network.write_text(text[: text.index("  gateways:")] + text[text.index("  perimeter:"):])

    with pytest.raises(RenderError, match="internet gateway"):
        render(lab_dir)


def test_server(lab_dir: Path) -> None:
    doc = render(lab_dir)
    resources = doc["resource"]

    eni = resources["aws_network_interface"]["app_1_eth0"]
    assert eni["private_ips"] == ["10.0.1.10"]
    assert eni["security_groups"] == ["${aws_security_group.ssh.id}"]

    instance = resources["aws_instance"]["app_1"]
    assert instance["ami"] == "ami-0123456789abcdef0"
    assert instance["root_block_device"] == {"volume_size": 30, "volume_type": "gp3"}
    assert instance["network_interface"] == [
        {"network_interface_id": "${aws_network_interface.app_1_eth0.id}", "device_index": 0}
    ]
    assert instance["user_data"] == "Write-Host $${env:COMPUTERNAME}\n"
    assert instance["user_data_replace_on_change"] is True
    assert doc["output"]["servers"]["value"]["app-1"]["public_ip"] is None


def test_public_interface(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server.yaml", "segment: subnet-2\n      address: 10.0.1.10",
         "segment: subnet-1\n      address: 10.0.0.10\n      public: true")

    doc = render(lab_dir)

    assert doc["resource"]["aws_eip"]["app_1_eth0"]["network_interface"] == "${aws_network_interface.app_1_eth0.id}"
    assert doc["resource"]["aws_instance"]["app_1"]["depends_on"] == ["aws_eip.app_1_eth0"]
    assert doc["output"]["servers"]["value"]["app-1"]["public_ip"] == "${aws_eip.app_1_eth0.public_ip}"


def test_public_interface_on_private_segment(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server.yaml", "address: 10.0.1.10", "address: 10.0.1.10\n      public: true")

    with pytest.raises(RenderError, match="has no internet gateway"):
        render(lab_dir)

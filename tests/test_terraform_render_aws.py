from pathlib import Path

import pytest

from attack_range_infrastructure.terraform.renderers import AwsRenderer, RenderError
from conftest import edit, load_cyber_range


def render(path: Path) -> dict:
    return AwsRenderer().render(load_cyber_range(path, "aws"))


def test_network(ar_template_dir: Path) -> None:
    doc = render(ar_template_dir)
    resources = doc["resource"]

    assert doc["provider"]["aws"]["region"] == "eu-central-1"
    assert resources["aws_vpc"]["vpc"]["cidr_block"] == "10.0.0.0/16"
    assert resources["aws_subnet"]["mgmt"]["cidr_block"] == "10.0.2.0/24"
    assert resources["aws_subnet"]["mgmt"]["availability_zone"] == "eu-central-1a"
    assert resources["aws_nat_gateway"]["egress"]["subnet_id"] == "${aws_subnet.public.id}"


def test_routing(ar_template_dir: Path) -> None:
    routes = render(ar_template_dir)["resource"]["aws_route"]

    assert routes["public_internet"]["gateway_id"] == "${aws_internet_gateway.igw.id}"
    assert routes["mgmt_internet"]["nat_gateway_id"] == "${aws_nat_gateway.egress.id}"


def test_filters_and_perimeter(lab_dir: Path) -> None:
    resources = render(lab_dir)["resource"]

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
    assert doc["output"]["servers"]["value"]["app-1"]["public_ip"] is None


def test_public_interface(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server.yaml", "segment: subnet-2\n      address: 10.0.1.10",
         "segment: subnet-1\n      address: 10.0.0.10\n      public: true")

    doc = render(lab_dir)

    assert doc["resource"]["aws_eip"]["app_1_eth0"]["network_interface"] == "${aws_network_interface.app_1_eth0.id}"
    assert doc["output"]["servers"]["value"]["app-1"]["public_ip"] == "${aws_eip.app_1_eth0.public_ip}"


def test_public_interface_on_private_segment(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server.yaml", "address: 10.0.1.10", "address: 10.0.1.10\n      public: true")

    with pytest.raises(RenderError, match="has no internet gateway"):
        render(lab_dir)

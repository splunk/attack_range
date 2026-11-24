from pathlib import Path

import pytest

from attack_range_infrastructure.terraform.renderers import RenderError, VmwareRenderer
from conftest import RESOURCE_PREFIX, RESOURCE_USER, edit, identified, load_cyber_range


def render(path: Path) -> dict:
    return VmwareRenderer().render(identified(load_cyber_range(path, "vmware")))


def test_existing_objects(lab_dir: Path) -> None:
    data = render(lab_dir)["data"]

    assert data["vsphere_datacenter"]["network"] == {"name": "dc1"}
    assert data["vsphere_network"]["subnet_2"]["name"] == "pg-app"
    assert data["vsphere_compute_cluster"]["app_1"]["name"] == "cluster-1"
    assert data["vsphere_virtual_machine"]["app_1_template"]["name"] == "ubuntu-24.04"


def test_server(lab_dir: Path) -> None:
    doc = render(lab_dir)
    vm = doc["resource"]["vsphere_virtual_machine"]["app_1"]

    assert vm["name"] == f"app-1-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    assert vm["clone"]["customize"]["linux_options"]["host_name"] == f"app-1-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    assert vm["num_cpus"] == 2
    assert vm["memory"] == 4096
    assert vm["disk"][0]["size"] == 30
    assert vm["network_interface"][0]["network_id"] == "${data.vsphere_network.subnet_2.id}"
    customize = vm["clone"]["customize"]
    assert customize["network_interface"] == [{"ipv4_address": "10.0.1.10", "ipv4_netmask": 24}]
    assert customize["ipv4_gateway"] == "10.0.1.1"
    assert vm["extra_config"]["guestinfo.userdata.encoding"] == "base64"


def test_missing_port_group(lab_dir: Path) -> None:
    edit(lab_dir / "lab.network-binding.vmware.yaml", "      subnet-2:\n        portGroup: pg-app\n", "")

    with pytest.raises(RenderError, match="no port group"):
        render(lab_dir)

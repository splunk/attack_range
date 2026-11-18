import base64
from pathlib import Path

from attack_range_infrastructure.terraform.renderers import AzureRenderer
from conftest import VALID_KEY, edit, load_cyber_range


def render(path: Path) -> dict:
    return AzureRenderer().render(load_cyber_range(path, "azure"))


def test_network(lab_dir: Path) -> None:
    resources = render(lab_dir)["resource"]

    assert resources["azurerm_resource_group"]["network"]["name"] == "lab"
    assert resources["azurerm_virtual_network"]["network"]["address_space"] == ["10.0.0.0/16"]
    assert resources["azurerm_subnet"]["subnet_2"]["address_prefixes"] == ["10.0.1.0/24"]
    assert resources["azurerm_subnet"]["subnet_2"]["default_outbound_access_enabled"] is False
    assert resources["azurerm_subnet_nat_gateway_association"]["subnet_2"]["nat_gateway_id"] == (
        "${azurerm_nat_gateway.egress.id}"
    )


def test_perimeter_on_subnet_and_filters_on_nic(lab_dir: Path) -> None:
    resources = render(lab_dir)["resource"]
    rules = resources["azurerm_network_security_rule"]

    perimeter = rules["subnet_subnet_1_AllowPerimeterInbound"]
    assert perimeter["source_address_prefixes"] == ["203.0.113.10/32"]
    assert resources["azurerm_subnet_network_security_group_association"]["subnet_subnet_1"]["subnet_id"] == (
        "${azurerm_subnet.subnet_1.id}"
    )

    ssh = rules["nic_app_1_eth0_ssh_0"]
    assert ssh["direction"] == "Inbound"
    assert ssh["protocol"] == "Tcp"
    assert ssh["destination_port_ranges"] == ["22"]
    assert ssh["priority"] == 100
    assert rules["nic_app_1_eth0_DenyAllInbound"]["priority"] == 4096
    assert "app_1_eth0" in resources["azurerm_network_interface_security_group_association"]


def test_linux_server(lab_dir: Path) -> None:
    doc = render(lab_dir)
    vm = doc["resource"]["azurerm_linux_virtual_machine"]["app_1"]

    assert vm["size"] == "Standard_B2s"
    assert vm["admin_ssh_key"] == [{"username": "ubuntu", "public_key": VALID_KEY}]
    assert vm["source_image_reference"]["offer"] == "ubuntu-24_04-lts"
    assert vm["os_disk"]["disk_size_gb"] == 30
    assert base64.b64decode(vm["custom_data"]).decode().startswith("Write-Host")
    nic = doc["resource"]["azurerm_network_interface"]["app_1_eth0"]["ip_configuration"][0]
    assert nic["private_ip_address"] == "10.0.1.10"


def test_windows_server(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server-binding.azure.yaml", "  azure:\n", "  azure:\n    adminPasswordSecret: app-1-password\n")

    doc = render(lab_dir)

    vm = doc["resource"]["azurerm_windows_virtual_machine"]["app_1"]
    assert vm["admin_password"] == "${var.app_1_password}"
    assert "admin_ssh_key" not in vm
    assert doc["variable"]["app_1_password"]["sensitive"] is True

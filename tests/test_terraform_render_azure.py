import base64
from pathlib import Path

import pytest

from attack_range.application.cyber_range import CyberRangeError
from attack_range_infrastructure.terraform.renderers import AzureRenderer
from attack_range_infrastructure.terraform.wireguard import load_gateway
from conftest import REPO, RESOURCE_PREFIX, RESOURCE_USER, VALID_KEY, edit, identified, load_cyber_range


def render(path: Path) -> dict:
    return AzureRenderer().render(identified(load_cyber_range(path, "azure")))


def test_wireguard_gateway(lab_dir: Path) -> None:
    doc = render(lab_dir)
    resources = doc["resource"]

    vm = resources["azurerm_linux_virtual_machine"]["wireguard"]
    server, binding = load_gateway("azure")
    settings = binding.spec.azure
    image = settings.image
    assert image is not None
    assert vm["size"] == settings.size
    assert vm["admin_username"] == server.spec.access.username
    assert vm["os_disk"]["disk_size_gb"] == settings.os_disk.size_gib
    assert "custom_data" not in vm
    assert vm["source_image_reference"] == {
        "publisher": image.publisher,
        "offer": image.offer,
        "sku": image.sku,
        "version": image.version,
    }
    nic = resources["azurerm_network_interface"]["wireguard"]
    assert nic["ip_forwarding_enabled"] is True
    assert nic["ip_configuration"][0]["subnet_id"] == "${azurerm_subnet.subnet_1.id}"
    assert resources["azurerm_public_ip"]["wireguard"]["allocation_method"] == "Static"
    rule = resources["azurerm_network_security_rule"]["wireguard_AllowWireGuard"]
    assert rule["protocol"] == "Udp" and rule["destination_port_range"] == "51820"
    assert "wireguard" not in doc["output"]["servers"]["value"]
    assert doc["output"]["wireguard"]["value"]["public_ip"] == "${azurerm_public_ip.wireguard.ip_address}"


def test_network(lab_dir: Path) -> None:
    resources = render(lab_dir)["resource"]

    assert resources["azurerm_resource_group"]["network"]["name"] == f"lab-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    assert resources["azurerm_virtual_network"]["network"]["name"] == f"lab-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    assert resources["azurerm_subnet"]["subnet_2"]["name"] == f"subnet-2-{RESOURCE_PREFIX}-{RESOURCE_USER}"
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
    assert resources["azurerm_network_security_group"]["nic_app_1_eth0"]["name"] == (
        f"app-1-eth0-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    )


def test_linux_server(lab_dir: Path) -> None:
    doc = render(lab_dir)
    vm = doc["resource"]["azurerm_linux_virtual_machine"]["app_1"]

    assert vm["name"] == f"app-1-{RESOURCE_PREFIX}-{RESOURCE_USER}"
    assert vm["size"] == "Standard_B2s"
    assert vm["admin_ssh_key"] == [{"username": "ubuntu", "public_key": VALID_KEY}]
    assert vm["source_image_reference"]["offer"] == "ubuntu-24_04-lts"
    assert vm["os_disk"]["disk_size_gb"] == 30
    assert base64.b64decode(vm["custom_data"]).decode().startswith("Write-Host")
    nic = doc["resource"]["azurerm_network_interface"]["app_1_eth0"]["ip_configuration"][0]
    assert nic["private_ip_address"] == "10.0.1.10"


def test_image_name_and_owner_select_the_newest_version() -> None:
    doc = render(REPO / "tmp" / "ar_template_azure")

    assert doc["data"]["azurerm_platform_image"]["splunk"] == {
        "location": "uksouth",
        "publisher": "Canonical",
        "offer": "0001-com-ubuntu-server-jammy",
        "sku": "22_04-lts",
    }
    splunk = doc["resource"]["azurerm_linux_virtual_machine"]["splunk"]["source_image_reference"]
    assert splunk["publisher"] == "Canonical"
    assert splunk["version"] == "${data.azurerm_platform_image.splunk.version}"
    windows = doc["resource"]["azurerm_windows_virtual_machine"]["win"]["source_image_reference"]
    assert windows["publisher"] == "MicrosoftWindowsServer"
    assert windows["offer"] == "WindowsServer"
    assert windows["sku"] == "2022-datacenter-g2"
    assert windows["version"] == "${data.azurerm_platform_image.win.version}"
    extension = doc["resource"]["azurerm_virtual_machine_extension"]["win_bootstrap"]
    assert extension["type"] == "CustomScriptExtension"
    assert "EncodedCommand" in extension["protected_settings"]


def test_image_lookup_needs_publisher_offer_and_sku(lab_dir: Path) -> None:
    edit(
        lab_dir / "lab.server-binding.azure.yaml",
        "    image:\n      publisher: Canonical\n      offer: ubuntu-24_04-lts\n      sku: server\n      version: latest\n",
        "    image_publisher: Canonical\n    image_offer: ubuntu-24_04-lts\n",
    )

    with pytest.raises(CyberRangeError, match="imagePublisher, imageOffer, and imageSku are set together"):
        load_cyber_range(lab_dir, "azure")


def test_windows_server(lab_dir: Path) -> None:
    edit(lab_dir / "lab.server-binding.azure.yaml", "  azure:\n", "  azure:\n    adminPasswordSecret: app-1-password\n")

    doc = render(lab_dir)

    vm = doc["resource"]["azurerm_windows_virtual_machine"]["app_1"]
    assert vm["name"] == f"app-1-{RESOURCE_PREFIX}"
    assert vm["computer_name"] == f"app-1-{RESOURCE_PREFIX}"
    assert vm["admin_password"] == "${var.app_1_password}"
    assert "admin_ssh_key" not in vm
    assert doc["variable"]["app_1_password"]["sensitive"] is True

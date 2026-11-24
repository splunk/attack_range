from ipaddress import IPv4Network

import pytest

from attack_range_infrastructure.terraform.wireguard import (
    WireGuardError,
    ansible_step,
    client_config_with_endpoint,
    listen_port,
    load_gateway,
    overlay_network,
    prepare_ansible,
    role_variables,
)


def test_gateway_config_is_a_server_and_its_bindings() -> None:
    aws_server, aws_binding = load_gateway("aws")
    azure_server, azure_binding = load_gateway("azure")

    assert aws_server.metadata.name == azure_server.metadata.name == "wireguard"
    assert aws_server.spec.access.username == azure_server.spec.access.username
    assert aws_binding.spec.provider == "aws"
    assert azure_binding.spec.provider == "azure"
    assert aws_binding.spec.aws.instance_type
    assert azure_binding.spec.azure.size
    assert azure_binding.spec.azure.image is not None


def test_gateway_ansible_job_supplies_the_role_and_the_range_addresses(tmp_path) -> None:
    server, _ = load_gateway("aws")

    assert ansible_step(server).role == "attack_range.wireguard"
    assert listen_port(server) == 51820
    values = role_variables(server, IPv4Network("10.0.0.0/16"), "203.0.113.10", "aws")
    assert values["vpn_address"] == "10.255.255.1/24"
    assert values["vpn_clients"] == [{"name": "client1", "address": "10.255.255.2/32"}]
    assert values["vpn_allowed_ips"] == "10.0.0.0/16"
    assert values["vpn_endpoint"] == "203.0.113.10"
    assert values["vpn_physical_interface"] == "ens5"

    prepare_ansible(
        tmp_path,
        host="203.0.113.10",
        username=server.spec.access.username,
        key_path=tmp_path / "id_rsa",
        server=server,
        address_space=IPv4Network("10.0.0.0/16"),
        endpoint="203.0.113.10",
        provider="aws",
    )
    assert "attack_range.wireguard" in (tmp_path / "provision.yml").read_text()
    assert "roles_path" in (tmp_path / "ansible.cfg").read_text()


def test_overlay_stays_outside_the_range() -> None:
    assert overlay_network(IPv4Network("10.0.0.0/16")) == IPv4Network("10.255.255.0/24")


def test_overlay_rejects_an_address_space_that_covers_every_candidate() -> None:
    with pytest.raises(WireGuardError, match="no wireguard overlay"):
        overlay_network(IPv4Network("0.0.0.0/0"))


def test_client_config_uses_the_gateway_address() -> None:
    config = client_config_with_endpoint(
        "[Peer]\nEndpoint = REPLACE_ENDPOINT:51820\n",
        "203.0.113.10",
    )

    assert "Endpoint = 203.0.113.10:51820" in config
    assert "REPLACE_ENDPOINT" not in config

"""Order of guest configuration after infrastructure has been applied.

The WireGuard gateway comes first. The operator connects, and only then are the
other servers provisioned, because those guests are reached through the tunnel.
"""

from pathlib import Path
from typing import Any, Optional

from attack_range.application.cyber_range import CyberRange
from attack_range.application.guest_provisioner import GuestProvisioner
from attack_range.application.operator import Operator
from attack_range.application.provisioner import ProvisionerError


def provision_guests(
    cyber_range: CyberRange,
    outputs: dict[str, Any],
    guests: GuestProvisioner,
    operator: Operator,
    *,
    reuse_vpn: bool = False,
    servers: Optional[set[str]] = None,
) -> dict[str, Any]:
    """Provision the gateway, wait for the VPN, then provision the other servers.

    An update reuses the client configuration already stored for the range. It does not
    install WireGuard again. It continues once the existing tunnel reaches the gateway.
    `servers` limits provisioning to those guests. `None` provisions every server that
    declares steps.
    """
    stored = dict(outputs)
    addresses = _server_addresses(cyber_range, stored, servers)
    public_ip = _gateway_address(cyber_range, stored)
    if public_ip is not None and (not reuse_vpn or addresses):
        existing = guests.existing_gateway(cyber_range) if reuse_vpn else None
        if existing is not None:
            _require_existing_vpn(guests, operator, existing.path, _private_address(stored))
            stored["wireguard"] = {**stored["wireguard"], "client_config": str(existing.path)}
        else:
            gateway = guests.provision_gateway(cyber_range, public_ip)
            operator.connect_vpn(gateway.text)
            stored["wireguard"] = {**stored["wireguard"], "client_config": str(gateway.path)}
    if addresses:
        guests.provision_servers(cyber_range, addresses)
    return stored


def _require_existing_vpn(
    guests: GuestProvisioner, operator: Operator, path: Path, private_ip: str
) -> None:
    """Wait until the tunnel that is already configured can reach the gateway."""
    while not guests.vpn_reaches(private_ip):
        operator.confirm_vpn(path)


def _private_address(outputs: dict[str, Any]) -> str:
    wireguard = outputs.get("wireguard")
    private_ip = wireguard.get("private_ip") if isinstance(wireguard, dict) else None
    if not isinstance(private_ip, str) or not private_ip:
        raise ProvisionerError("wireguard gateway has no private address")
    return private_ip


def _gateway_address(cyber_range: CyberRange, outputs: dict[str, Any]) -> Optional[str]:
    if cyber_range.provider not in ("aws", "azure"):
        return None
    wireguard = outputs.get("wireguard")
    if not isinstance(wireguard, dict):
        return None
    public_ip = wireguard.get("public_ip")
    if not isinstance(public_ip, str) or not public_ip:
        raise ProvisionerError("wireguard gateway has no public address")
    return public_ip


def _server_addresses(
    cyber_range: CyberRange, outputs: dict[str, Any], only: Optional[set[str]] = None
) -> dict[str, str]:
    """Private addresses of servers that declare provisioning steps."""
    published = outputs.get("servers")
    if not isinstance(published, dict):
        return {}
    addresses: dict[str, str] = {}
    for server in cyber_range.servers:
        if only is not None and server.metadata.name not in only:
            continue
        if not server.spec.provisioning:
            continue
        entry = published.get(server.metadata.name)
        if entry is None:
            continue
        private_ip = entry.get("private_ip") if isinstance(entry, dict) else None
        if not isinstance(private_ip, str) or not private_ip:
            raise ProvisionerError(f"server '{server.metadata.name}' has no private address")
        addresses[server.metadata.name] = private_ip
    return addresses

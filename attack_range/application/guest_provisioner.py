"""Port for configuring guests after their infrastructure exists."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .cyber_range import CyberRange


@dataclass(frozen=True)
class GatewayConfig:
    """WireGuard client configuration fetched from the gateway."""

    text: str
    path: Path


class GuestProvisioner(ABC):
    """Configures the WireGuard gateway, then the servers declared in the range."""

    @abstractmethod
    def provision_gateway(self, cyber_range: CyberRange, public_ip: str) -> GatewayConfig:
        """Install WireGuard on the gateway and return the client configuration."""

    @abstractmethod
    def existing_gateway(self, cyber_range: CyberRange) -> GatewayConfig | None:
        """Return the client configuration already stored for this range."""

    @abstractmethod
    def vpn_reaches(self, address: str) -> bool:
        """Return whether `address` accepts a connection through the current tunnel."""

    @abstractmethod
    def provision_servers(self, cyber_range: CyberRange, addresses: dict[str, str]) -> None:
        """Run each server's provisioning steps. `addresses` maps a server name to its private IP."""


class NullGuestProvisioner(GuestProvisioner):
    """Leaves guests unconfigured. Tests use this when they only exercise infrastructure."""

    def provision_gateway(self, cyber_range: CyberRange, public_ip: str) -> GatewayConfig:
        return GatewayConfig(text="", path=Path())

    def existing_gateway(self, cyber_range: CyberRange) -> GatewayConfig | None:
        return None

    def vpn_reaches(self, address: str) -> bool:
        return True

    def provision_servers(self, cyber_range: CyberRange, addresses: dict[str, str]) -> None:
        return

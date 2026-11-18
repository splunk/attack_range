"""Cyber range: one Network, its Servers, and the bindings that realize them on one provider."""

from dataclasses import dataclass, field
from typing import Optional, Sequence
from uuid import UUID

from attack_range.domain.entities import Network, NetworkBinding, Server, ServerBinding
from attack_range.domain.entities.common import Provider

Document = Network | NetworkBinding | Server | ServerBinding


class CyberRangeError(ValueError):
    """Raised when a set of lab documents does not form a consistent cyber range."""


@dataclass(frozen=True)
class CyberRange:
    """Validated set of documents realized on a single provider."""

    network: Network
    network_binding: NetworkBinding
    servers: list[Server]
    server_bindings: dict[str, ServerBinding]
    provider: Provider
    bootstrap_files: dict[str, str] = field(default_factory=dict)
    """Contents of each `bootstrap.userData` file, keyed by file name."""
    id: Optional[UUID] = None
    """Id of the registered range. Templates that are only planned have none."""
    local_state: bool = False
    """Keep provisioner state next to the generated code instead of the provider's default store."""

    @property
    def name(self) -> str:
        return self.network.metadata.name

    @property
    def location(self) -> str:
        return self.network_binding.spec.location

    @property
    def tags(self) -> dict[str, str]:
        """Tags for every resource of the range, from the NetworkBinding."""
        return self.network_binding.spec.tags

    def binding(self, server: Server) -> ServerBinding:
        """Return the ServerBinding of this server."""
        return self.server_bindings[server.metadata.name]

    def user_data(self, server: Server) -> Optional[str]:
        """Return the bootstrap file contents of this server."""
        if server.spec.bootstrap is None:
            return None
        return self.bootstrap_files[server.spec.bootstrap.user_data]


def assemble_cyber_range(
    documents: Sequence[Document],
    provider: Optional[Provider] = None,
    bootstrap_files: Optional[dict[str, str]] = None,
) -> CyberRange:
    """Check that the documents form one cyber range and keep the bindings of `provider`.

    Without a provider, the documents must bind the network to exactly one provider.
    """
    networks = [document for document in documents if isinstance(document, Network)]
    all_network_bindings = [document for document in documents if isinstance(document, NetworkBinding)]
    servers = [document for document in documents if isinstance(document, Server)]

    if provider is None:
        provider = _only_provider(all_network_bindings)
    network_bindings = [binding for binding in all_network_bindings if binding.spec.provider == provider]
    server_bindings = [
        document for document in documents
        if isinstance(document, ServerBinding) and document.spec.provider == provider
    ]

    if len(networks) != 1:
        raise CyberRangeError(f"needs exactly one Network document, found {len(networks)}")
    network = networks[0]
    network_name = network.metadata.name

    matching = [binding for binding in network_bindings if binding.spec.network == network_name]
    if len(matching) != 1 or len(network_bindings) != 1:
        raise CyberRangeError(
            f"needs exactly one {provider} NetworkBinding for network '{network_name}', "
            f"found {len(network_bindings)}"
        )
    network_binding = matching[0]

    _check_servers(network, servers)
    bindings_by_server = _bind_servers(servers, server_bindings, provider)

    location = network_binding.spec.location
    for binding in bindings_by_server.values():
        if binding.spec.location != location:
            raise CyberRangeError(
                f"server binding '{binding.metadata.name}' location '{binding.spec.location}' "
                f"differs from network binding location '{location}'"
            )

    files = bootstrap_files or {}
    for server in servers:
        if server.spec.bootstrap is not None and server.spec.bootstrap.user_data not in files:
            raise CyberRangeError(
                f"server '{server.metadata.name}' user data '{server.spec.bootstrap.user_data}' is missing"
            )

    return CyberRange(
        network=network,
        network_binding=network_binding,
        servers=servers,
        server_bindings=bindings_by_server,
        provider=provider,
        bootstrap_files=dict(files),
    )


def _only_provider(network_bindings: list[NetworkBinding]) -> Provider:
    providers = sorted({binding.spec.provider for binding in network_bindings})
    if len(providers) != 1:
        found = ", ".join(providers) or "none"
        raise CyberRangeError(f"choose a provider; the NetworkBindings name {found}")
    return providers[0]


def _check_servers(network: Network, servers: list[Server]) -> None:
    network_name = network.metadata.name
    segment_names = {segment.name for segment in network.spec.segments}
    filter_names = {filter_.name for filter_ in network.spec.filters}
    seen: set[str] = set()

    for server in servers:
        name = server.metadata.name
        if name in seen:
            raise CyberRangeError(f"duplicate server name '{name}'")
        seen.add(name)
        if server.spec.network != network_name:
            raise CyberRangeError(f"server '{name}' names unknown network '{server.spec.network}'")
        for interface in server.spec.interfaces:
            if interface.segment not in segment_names:
                raise CyberRangeError(
                    f"server '{name}' interface '{interface.name}' names unknown segment '{interface.segment}'"
                )
            for filter_name in interface.filters:
                if filter_name not in filter_names:
                    raise CyberRangeError(
                        f"server '{name}' interface '{interface.name}' names unknown filter '{filter_name}'"
                    )
            if interface.address != "auto":
                cidr = network.spec.segment_cidrs()[interface.segment]
                if interface.address not in cidr:
                    raise CyberRangeError(
                        f"server '{name}' interface '{interface.name}' address {interface.address} "
                        f"is outside segment '{interface.segment}' {cidr}"
                    )


def _bind_servers(
    servers: list[Server], server_bindings: list[ServerBinding], provider: Provider
) -> dict[str, ServerBinding]:
    server_names = {server.metadata.name for server in servers}
    bindings: dict[str, ServerBinding] = {}

    for binding in server_bindings:
        server_name = binding.spec.server
        if server_name not in server_names:
            raise CyberRangeError(f"server binding '{binding.metadata.name}' names unknown server '{server_name}'")
        if server_name in bindings:
            raise CyberRangeError(f"server '{server_name}' has more than one {provider} ServerBinding")
        bindings[server_name] = binding

    missing = sorted(server_names - bindings.keys())
    if missing:
        raise CyberRangeError(f"server '{missing[0]}' has no {provider} ServerBinding")
    return bindings

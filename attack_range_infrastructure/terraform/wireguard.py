"""WireGuard gateway shared by the AWS and Azure renderers.

Ansible provisions the guest from the role named on the server document. Deploy writes
the gateway, then get_config fetches the client file, the same two passes Attack Range 2 uses.
"""

from ipaddress import IPv4Network
from pathlib import Path
from typing import Any

import yaml

from attack_range.domain.entities import Server, ServerBinding, parse_document
from attack_range.domain.entities.common import Provider
from attack_range.domain.entities.server import AnsibleStep

LISTEN_PORT = 51820
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config" / "wireguard"
ROLES_DIR = CONFIG_DIR / "roles"


class WireGuardError(ValueError):
    """Raised when the gateway cannot be placed on this range."""


OVERLAYS = (
    IPv4Network("10.255.255.0/24"),
    IPv4Network("172.31.255.0/24"),
    IPv4Network("192.168.255.0/24"),
    IPv4Network("100.64.255.0/24"),
)


def load_gateway(provider: Provider) -> tuple[Server, ServerBinding]:
    """Read the platform gateway from config/wireguard. The range supplies placement and location."""
    server = _parse(CONFIG_DIR / "wireguard.server.yaml", Server)
    binding = _parse(CONFIG_DIR / f"wireguard.server-binding.{provider}.yaml", ServerBinding)
    if binding.spec.provider != provider or binding.spec.server != server.metadata.name:
        raise WireGuardError(f"wireguard binding does not match the {provider} gateway server")
    return server, binding


def _parse(path: Path, expected: type[Server] | type[ServerBinding]) -> Server | ServerBinding:
    if not path.is_file():
        raise WireGuardError(f"wireguard config {path} is missing")
    try:
        document = parse_document(yaml.safe_load(path.read_text()))
    except (yaml.YAMLError, ValueError) as error:
        raise WireGuardError(f"{path.name}: {error}") from error
    if not isinstance(document, expected):
        raise WireGuardError(f"{path.name} is not a {expected.__name__}")
    return document


def overlay_network(address_space: IPv4Network) -> IPv4Network:
    """A tunnel network that is not part of the range address space."""
    for candidate in OVERLAYS:
        if not candidate.overlaps(address_space):
            return candidate
    raise WireGuardError("no wireguard overlay is free of the range address space")


def ansible_step(server: Server) -> AnsibleStep:
    """The one Ansible job declared on the gateway server."""
    steps = [step for step in server.spec.provisioning if isinstance(step, AnsibleStep)]
    if len(steps) != 1:
        raise WireGuardError("the wireguard server needs one ansible provisioning step")
    return steps[0]


CLIENT_NAME = "client1"
PHYSICAL_INTERFACE = {"aws": "ens5", "azure": "eth0"}


def listen_port(server: Server) -> int:
    """UDP port from the gateway's Ansible vars. The security group opens this port."""
    raw = ansible_step(server).vars.get("vpn_listen_port", LISTEN_PORT)
    try:
        port = int(raw)
    except (TypeError, ValueError) as error:
        raise WireGuardError("vpn_listen_port must be a port number") from error
    if not 1 <= port <= 65535:
        raise WireGuardError("vpn_listen_port must be a port number")
    return port


def role_variables(server: Server, address_space: IPv4Network, endpoint: str, provider: Provider) -> dict[str, Any]:
    """Vars from the server document, plus the addresses and NIC that depend on this range."""
    overlay = overlay_network(address_space)
    hosts = overlay.hosts()
    gateway = next(hosts)
    client = next(hosts)
    values = dict(ansible_step(server).vars)
    values["vpn_listen_port"] = listen_port(server)
    values["vpn_address"] = f"{gateway}/{overlay.prefixlen}"
    values["vpn_allowed_ips"] = str(address_space)
    values["vpn_endpoint"] = endpoint
    values["vpn_clients"] = [{"name": CLIENT_NAME, "address": f"{client}/32"}]
    values["vpn_clients_dir"] = "/etc/wireguard"
    values.setdefault("vpn_physical_interface", PHYSICAL_INTERFACE.get(provider, "ens5"))
    return values


def prepare_ansible(
    directory: Path,
    *,
    host: str,
    username: str,
    key_path: Path,
    server: Server,
    address_space: IPv4Network,
    endpoint: str,
    provider: Provider,
) -> None:
    """Write the inventory and playbook that run the gateway role against one host."""
    step = ansible_step(server)
    role = ROLES_DIR / step.role
    if not (role / "tasks" / "main.yml").is_file():
        raise WireGuardError(f"ansible role {step.role} is not in {ROLES_DIR}")
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    (directory / "ansible.cfg").write_text(
        "[defaults]\n"
        "host_key_checking = False\n"
        "timeout = 30\n"
        "retry_files_enabled = False\n"
        "interpreter_python = auto_silent\n"
        f"roles_path = {ROLES_DIR}\n"
    )
    (directory / "inventory.yml").write_text(yaml.safe_dump({
        "all": {"hosts": {"wireguard": {
            "ansible_host": host,
            "ansible_user": username,
            "ansible_ssh_private_key_file": str(key_path),
            "ansible_ssh_common_args": "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15",
        }}},
    }, sort_keys=False))
    values = role_variables(server, address_space, endpoint, provider)
    values["client_config_local_dir"] = str(directory / "client_configs")
    (directory / "vars.yml").write_text(yaml.safe_dump(values, sort_keys=False))
    (directory / "provision.yml").write_text(yaml.safe_dump([{
        "hosts": "wireguard",
        "become": True,
        "roles": [step.role],
    }], sort_keys=False))


def access_sources(sources: list[IPv4Network] | None) -> list[str]:
    """Prefixes allowed to reach the gateway. Without a perimeter, the gateway is open."""
    if not sources:
        return ["0.0.0.0/0"]
    return [str(source) for source in sources]


def client_config_with_endpoint(config: str, public_ip: str, port: int = LISTEN_PORT) -> str:
    """Put the gateway's public address into a fetched client config."""
    if not config.strip():
        raise WireGuardError("wireguard client config is empty")
    endpoint = f"Endpoint = {public_ip}:{port}"
    rewritten: list[str] = []
    replaced = False
    for line in config.splitlines():
        if line.strip().startswith("Endpoint"):
            rewritten.append(endpoint)
            replaced = True
        else:
            rewritten.append(line)
    if not replaced:
        rewritten.append(endpoint)
    return "\n".join(rewritten).rstrip() + "\n"

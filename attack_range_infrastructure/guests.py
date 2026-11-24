"""Ansible implementation of the guest provisioner.

The gateway role runs first. Server roles run later, once the operator has enabled the VPN,
and they connect to each server's private address. Servers are provisioned together.
"""

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from attack_range.application.cyber_range import CyberRange
from attack_range.application.guest_provisioner import GatewayConfig, GuestProvisioner
from attack_range.application.operator import NullOperator, Operator
from attack_range.application.provisioner import NullProvisionLog, ProvisionLog, ProvisionerError
from attack_range.domain.entities.server import AnsibleStep, Server
from attack_range_infrastructure.command import CommandIdle, stream_command
from attack_range_infrastructure.keys import PRIVATE_KEY
from attack_range_infrastructure.storage.home import AttackRangeHome
from attack_range_infrastructure.terraform.wireguard import (
    CLIENT_NAME,
    WireGuardError,
    client_config_with_endpoint,
    listen_port,
    load_gateway,
    prepare_ansible,
)

# A step that prints nothing for this long is treated as hung. The operator can wait, retry, or abort.
IDLE_TIMEOUT = 300
# A play that fails is run this many times before the build stops.
ATTEMPTS = 3
# The gateway may still be booting. Unreachable attempts wait this long, then count as a failure.
SSH_WAIT = 300
RETRY_PAUSE = 10
SSH_OPTIONS = "-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15"
BUNDLED_ROLES = Path(__file__).resolve().parent / "config" / "roles"
# Homebrew installs GNU tar as gtar. Ansible unarchive rejects macOS BSD tar.
_GNU_TAR_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")
_UNREACHABLE = re.compile(r"unreachable=(\d+)")


class AnsibleGuestProvisioner(GuestProvisioner):
    """Runs the platform WireGuard role, then the roles declared on each server."""

    def __init__(
        self,
        home: AttackRangeHome,
        log: ProvisionLog | None = None,
        operator: Operator | None = None,
    ) -> None:
        self.home = home
        self.log = log or NullProvisionLog()
        self.operator = operator or NullOperator()
        self._prompt = threading.Lock()
        self._gnu_tar_dir: str | None = None

    def provision_gateway(self, cyber_range: CyberRange, public_ip: str) -> GatewayConfig:
        key = self._key(cyber_range)
        if cyber_range.id is None:
            raise ProvisionerError(f"cyber range '{cyber_range.name}' has no id")
        try:
            server = load_gateway(cyber_range.provider)[0]
        except WireGuardError as error:
            raise ProvisionerError(str(error)) from error
        directory = self.home.wireguard_config(cyber_range.id).parent
        try:
            prepare_ansible(
                directory,
                host=public_ip,
                username=server.spec.access.username,
                key_path=key,
                server=server,
                address_space=cyber_range.network.spec.address_space.cidr,
                endpoint=public_ip,
                provider=cyber_range.provider,
            )
        except WireGuardError as error:
            raise ProvisionerError(str(error)) from error
        self._ansible(directory, "deploy", retry=True)
        self._ansible(directory, "get_config", retry=False)
        fetched = directory / "client_configs" / f"{CLIENT_NAME}.conf"
        if not fetched.is_file():
            raise ProvisionerError(f"wireguard client config was not fetched to {fetched}")
        try:
            config = client_config_with_endpoint(fetched.read_text(), public_ip, listen_port(server))
        except WireGuardError as error:
            raise ProvisionerError(str(error)) from error
        path = self.home.wireguard_config(cyber_range.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.chmod(0o700)
        path.write_text(config)
        path.chmod(0o600)
        return GatewayConfig(text=config, path=path)

    def existing_gateway(self, cyber_range: CyberRange) -> GatewayConfig | None:
        """The client configuration written by an earlier build, when it is still on disk."""
        if cyber_range.id is None:
            return None
        path = self.home.wireguard_config(cyber_range.id)
        if not path.is_file():
            return None
        text = path.read_text()
        if not text.strip():
            return None
        return GatewayConfig(text=text, path=path)

    def vpn_reaches(self, address: str) -> bool:
        """The gateway's private address answers only when the tunnel is up."""
        try:
            with socket.create_connection((address, 22), timeout=3):
                return True
        except OSError:
            return False

    def provision_servers(self, cyber_range: CyberRange, addresses: dict[str, str]) -> None:
        servers = [server for server in cyber_range.servers if server.metadata.name in addresses]
        if not servers:
            return
        if cyber_range.id is None:
            raise ProvisionerError(f"cyber range '{cyber_range.name}' has no id")
        key = self._key(cyber_range)
        directory = self.home.range_dir(cyber_range.id) / "ansible"
        directory.mkdir(parents=True, exist_ok=True)
        if _stages_archives_on_controller(servers):
            self._require_gnu_tar()
        steps = _role_steps(servers)
        _write_server_play(directory, servers, addresses, key)
        collections = _collections(servers)
        if collections:
            self._play(
                directory,
                ["ansible-galaxy", "collection", "install", *collections, "-p", "collections"],
                f"ansible-galaxy collection install {' '.join(collections)}",
            )
        for step in steps:
            self._install_role(directory, step)
        names = [server.metadata.name for server in servers]
        if len(names) == 1:
            self._play(
                directory,
                ["ansible-playbook", "-i", "inventory.yml", "provision.yml"],
                "ansible-playbook servers",
            )
            return
        self._provision_together(directory, names)

    def _require_gnu_tar(self) -> None:
        """Ansible unpacks Splunk app archives on the controller, which needs GNU tar.

        On macOS the system tar is BSD tar. Stop and tell the operator how to install
        GNU tar rather than installing it for them.
        """
        path = os.environ.get("PATH", "")
        binary = _gnu_tar(os.environ.copy())
        if binary is None:
            install = "brew install gnu-tar" if sys.platform == "darwin" else "install GNU tar from your distribution"
            raise ProvisionerError(f"GNU tar is required to unpack Splunk apps on the controller. Install it with: {install}")
        directory = str(binary.parent)
        if directory not in path.split(os.pathsep):
            self._gnu_tar_dir = directory

    def _install_role(self, directory: Path, step: AnsibleStep) -> None:
        """Install one role from the repo, Ansible Galaxy, or the git repository on the step."""
        bundled = BUNDLED_ROLES / step.role / "tasks" / "main.yml"
        if step.repository is None and bundled.is_file():
            _link_role(directory, step.role, bundled.parent.parent)
            return
        if step.repository is None:
            self._play(
                directory,
                ["ansible-galaxy", "install", step.role, "-p", "roles"],
                f"ansible-galaxy install {step.role}",
            )
            return
        checkout = directory / "src" / step.role
        if checkout.exists():
            shutil.rmtree(checkout)
        command = ["git", "clone", "--depth", "1"]
        if step.revision is not None:
            command.extend(["--branch", step.revision])
        command.extend([str(step.repository), str(checkout)])
        label = f"git clone {step.role}" if step.revision is None else f"git clone {step.role} {step.revision}"
        self._play(directory, command, label)
        source = checkout / step.role_path if step.role_path else checkout
        if not (source / "tasks").is_dir():
            raise ProvisionerError(f"role '{step.role}' has no tasks directory at {source}")
        _link_role(directory, step.role, source)

    def _key(self, cyber_range: CyberRange) -> Path:
        if cyber_range.id is None:
            raise ProvisionerError(f"cyber range '{cyber_range.name}' has no id")
        key = self.home.keys_dir(cyber_range.id) / PRIVATE_KEY
        if not key.is_file():
            raise ProvisionerError(f"range has no SSH key at {key}")
        return key

    def _ansible(self, directory: Path, action: str, *, retry: bool) -> None:
        """Run one gateway play.

        A failed play is tried `ATTEMPTS` times. While `retry` is set, a gateway that
        does not accept SSH yet is tried again until `SSH_WAIT` seconds have passed.
        """
        command = [
            "ansible-playbook", "-i", "inventory.yml", "provision.yml",
            "-e", "@vars.yml", "-e", f"wireguard_action={action}",
        ]
        deadline = time.monotonic() + SSH_WAIT
        task_attempt = 0
        detail = ""
        title = f"ansible-playbook wireguard {action}"
        while True:
            label = title if task_attempt == 0 else f"{title} (retry {task_attempt})"
            completed = self._run(directory, command, label)
            if completed.returncode == 0:
                return
            detail = completed.stdout.strip()
            if retry and _host_unreachable(completed) and time.monotonic() < deadline:
                self.log.line("wireguard gateway is not reachable yet, retrying")
                time.sleep(RETRY_PAUSE)
                continue
            task_attempt += 1
            if task_attempt < ATTEMPTS:
                self.log.line(f"{title} failed, retrying ({task_attempt + 1}/{ATTEMPTS})")
                time.sleep(RETRY_PAUSE)
                continue
            raise ProvisionerError(f"could not provision the wireguard gateway: {detail}")

    def _provision_together(self, directory: Path, names: list[str]) -> None:
        """Run one playbook per server at the same time. Each server retries on its own."""
        errors: list[BaseException] = []
        errors_lock = threading.Lock()

        def run(name: str) -> None:
            try:
                self._play(
                    directory,
                    ["ansible-playbook", "-i", "inventory.yml", "provision.yml", "--limit", name],
                    f"ansible-playbook {name}",
                    log=_PrefixedLog(self.log, name),
                )
            except Exception as error:
                with errors_lock:
                    errors.append(error)

        with ThreadPoolExecutor(max_workers=len(names)) as pool:
            futures = [pool.submit(run, name) for name in names]
            for future in futures:
                future.result()
        if errors:
            raise ProvisionerError("\n".join(str(error) for error in errors))

    def _play(
        self, directory: Path, command: list[str], title: str, log: ProvisionLog | None = None
    ) -> None:
        """Run one command up to `ATTEMPTS` times. Raise when every attempt fails."""
        detail = ""
        for attempt in range(ATTEMPTS):
            label = title if attempt == 0 else f"{title} (retry {attempt})"
            completed = self._run(directory, command, label, log)
            if completed.returncode == 0:
                return
            detail = completed.stdout.strip()
            if attempt + 1 < ATTEMPTS:
                self.log.line(f"{title} failed, retrying ({attempt + 2}/{ATTEMPTS})")
                time.sleep(RETRY_PAUSE)
        raise ProvisionerError(f"{title} failed: {detail}")

    def _run(
        self, directory: Path, command: list[str], title: str, log: ProvisionLog | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Run one Ansible command. A hang asks the operator whether to retry, wait, or abort."""
        environment = os.environ.copy()
        environment["ANSIBLE_NOCOLOR"] = "1"
        environment["ANSIBLE_FORCE_COLOR"] = "0"
        if self._gnu_tar_dir:
            path = environment.get("PATH", "")
            if self._gnu_tar_dir not in path.split(os.pathsep):
                environment["PATH"] = self._gnu_tar_dir + (os.pathsep + path if path else "")
        sink = log or self.log
        attempt = 1
        while True:
            label = title if attempt == 1 else f"{title} (retry {attempt - 1})"
            self.log.line(label)
            try:
                return stream_command(
                    command,
                    directory,
                    sink,
                    environment,
                    idle_timeout=IDLE_TIMEOUT,
                    on_idle=lambda last, output, current=label: self._idle(current, last, output),
                )
            except CommandIdle:
                attempt += 1
                self.log.line(f"{label} hung with no output, retrying")
            except FileNotFoundError as error:
                raise ProvisionerError(f"{command[0]} is required to provision guests") from error

    def _idle(self, title: str, last: str, output: int) -> str:
        """Ask the operator about one hung command. Another prompt keeps this one reading."""
        if not self._prompt.acquire(blocking=False):
            return "later"
        try:
            return self.operator.hung_command(title, IDLE_TIMEOUT, last, output).value
        finally:
            self._prompt.release()


class _PrefixedLog(ProvisionLog):
    """Marks each line with the server it came from when several plays run together."""

    def __init__(self, inner: ProvisionLog, name: str) -> None:
        self._inner = inner
        self._name = name

    def line(self, text: str) -> None:
        self._inner.line(f"[{self._name}] {text}")


def _gnu_tar(environment: dict[str, str]) -> Path | None:
    """Return a GNU tar binary from PATH or the usual Homebrew locations."""
    directories = [directory for directory in environment.get("PATH", "").split(os.pathsep) if directory]
    for directory in (*directories, *_GNU_TAR_DIRS):
        for name in ("gtar", "tar"):
            binary = Path(directory) / name
            if not binary.is_file():
                continue
            if name == "gtar" or _tar_is_gnu(binary):
                return binary
    return None


def _tar_is_gnu(binary: Path) -> bool:
    try:
        completed = subprocess.run(
            [str(binary), "--version"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "gnu tar" in f"{completed.stdout}{completed.stderr}".lower()


def _stages_archives_on_controller(servers: list[Server]) -> bool:
    """The Splunk app tasks unpack archives on the controller."""
    for server in servers:
        for step in server.spec.provisioning:
            if not isinstance(step, AnsibleStep):
                continue
            if step.vars.get("deployment_task") == "configure_apps.yml":
                return True
    return False


def _link_role(directory: Path, name: str, source: Path) -> None:
    """Expose one role directory under the playbook's roles path."""
    roles = directory / "roles"
    roles.mkdir(parents=True, exist_ok=True)
    installed = roles / name
    if installed.is_symlink() or installed.is_file():
        installed.unlink()
    elif installed.exists():
        shutil.rmtree(installed)
    installed.symlink_to(source.resolve(), target_is_directory=True)


def _connection(server: Server, address: str, key: Path) -> dict[str, object]:
    """Ansible connection variables from `access`.

    Linux guests escalate with `ansible_become` on the host. A play-level `become`
    would also apply to tasks a role delegates to localhost, and the controller
    has no sudo password.
    """
    access = server.spec.access
    host: dict[str, object] = {"ansible_host": address, "ansible_user": access.username}
    if access.winrm is None:
        host["ansible_become"] = True
    if access.ssh_key is not None:
        host["ansible_ssh_private_key_file"] = str(key if access.ssh_key == "range" else Path(access.ssh_key))
        host["ansible_ssh_common_args"] = SSH_OPTIONS
        return host
    host["ansible_password"] = access.password
    winrm = access.winrm
    if winrm is None:
        return host
    host.update({
        "ansible_connection": "winrm",
        "ansible_port": winrm.port,
        "ansible_winrm_scheme": winrm.scheme,
        "ansible_winrm_transport": winrm.transport,
        "ansible_winrm_server_cert_validation": winrm.cert_validation,
        "ansible_winrm_operation_timeout_sec": winrm.timeout_seconds,
        "ansible_winrm_read_timeout_sec": winrm.timeout_seconds * 2,
        "ansible_winrm_connection_timeout": winrm.timeout_seconds,
    })
    if winrm.scheme == "http":
        host["ansible_winrm_message_encryption"] = "never"
    return host


def _host_unreachable(completed: subprocess.CompletedProcess[str]) -> bool:
    """Return whether Ansible failed because the host did not accept SSH."""
    if completed.returncode == 3 or "Failed to connect to the host via ssh" in completed.stdout:
        return True
    match = _UNREACHABLE.search(completed.stdout)
    return match is not None and match.group(1) != "0"


def _role_source(step: AnsibleStep) -> tuple[str | None, str | None, str | None]:
    """The checkout a step names. The role is installed once from this source."""
    repository = None if step.repository is None else str(step.repository)
    return repository, step.revision, step.role_path


def _role_steps(servers: list[Server]) -> list[AnsibleStep]:
    """Ansible steps, in first-use order, with the same role name kept once.

    A later step may repeat the role. Its repository, revision, and rolePath must match
    the first declaration, which is the one that is installed.
    """
    steps: list[AnsibleStep] = []
    chosen: dict[str, AnsibleStep] = {}
    for server in servers:
        for step in server.spec.provisioning:
            if not isinstance(step, AnsibleStep):
                raise ProvisionerError(
                    f"server '{server.metadata.name}' provisioning step '{step.type}' is not supported"
                )
            earlier = chosen.get(step.role)
            if earlier is None:
                chosen[step.role] = step
                steps.append(step)
                continue
            if _role_source(earlier) != _role_source(step):
                raise ProvisionerError(
                    f"role '{step.role}' is used twice with different repository, revision, or rolePath"
                )
    return steps


def _collections(servers: list[Server]) -> list[str]:
    """Collection names, in first-use order, with duplicates removed.

    A role can run twice with different variables, so this reads every step.
    """
    names: list[str] = []
    for server in servers:
        for step in server.spec.provisioning:
            if not isinstance(step, AnsibleStep):
                continue
            for name in step.collections:
                if name not in names:
                    names.append(name)
    return names


def _write_server_play(directory: Path, servers: list[Server], addresses: dict[str, str], key: Path) -> None:
    hosts: dict[str, dict[str, object]] = {}
    children: dict[str, dict[str, dict[str, object]]] = {}
    plays = []
    for server in servers:
        host = _connection(server, addresses[server.metadata.name], key)
        roles = []
        for step in server.spec.provisioning:
            assert isinstance(step, AnsibleStep)
            if "ansible_python_interpreter" in step.vars:
                host["ansible_python_interpreter"] = step.vars["ansible_python_interpreter"]
            for group in step.groups:
                group_hosts = children.setdefault(group, {"hosts": {}})["hosts"]
                group_hosts[server.metadata.name] = {}
            role: dict[str, object] = {"role": step.role, **step.vars}
            if step.environment:
                role["environment"] = step.environment
            roles.append(role)
        hosts[server.metadata.name] = host
        play: dict[str, object] = {"hosts": server.metadata.name, "roles": roles}
        plays.append(play)
    all_group: dict[str, object] = {"hosts": hosts}
    if children:
        all_group["children"] = children
    inventory = {"all": all_group}
    (directory / "ansible.cfg").write_text(
        "[defaults]\n"
        "host_key_checking = False\n"
        "timeout = 30\n"
        "retry_files_enabled = False\n"
        "interpreter_python = auto_silent\n"
        f"roles_path = {directory / 'roles'}\n"
        f"collections_path = {directory / 'collections'}\n"
    )
    (directory / "inventory.yml").write_text(yaml.safe_dump(inventory, sort_keys=False))
    play = directory / "provision.yml"
    play.write_text(yaml.safe_dump(plays, sort_keys=False))
    play.chmod(0o600)

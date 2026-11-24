import os
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.markup import escape
from rich.measure import Measurement
from rich.table import Table
from rich.theme import Theme

from attack_range.application.cyber_range import CyberRange
from attack_range.application.provisioner import ProvisionLog
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.entities.server import Server
from attack_range.domain.entities.server_binding import (
    AwsServerBindingSpec,
    AzureServerBindingSpec,
    ServerBinding,
    VmwareServerBindingSpec,
)
from attack_range.domain.value_objects.range_state import RangeState
from attack_range.use_cases.get_range import GetRangeOutputBoundary, GetRangeOutputDto
from attack_range.use_cases.list_ranges import ListRangesOutputBoundary, ListRangesOutputDto
from attack_range.use_cases.provision import ProvisionOutputBoundary, ProvisionOutputDto
from attack_range.use_cases.prune_ranges import PruneRangesOutputBoundary, PruneRangesOutputDto
from attack_range.use_cases.upload_image import UploadImageOutputBoundary, UploadImageOutputDto

_THEME = Theme(
    {
        "error": "bold red",
        "ok": "bold green",
        "path": "bold cyan",
        "field": "bold",
        "summary": "dim",
    }
)

_DONE = {"plan": "planned", "build": "built", "destroy": "destroyed", "update": "updated"}


def _console(stderr: bool = False, width: Optional[int] = None) -> Console:
    return Console(stderr=stderr, width=width, theme=_THEME, soft_wrap=True, highlight=False, emoji=False)


class CliUploadPresenter(UploadImageOutputBoundary):
    """Print the managed image id, or the reason the upload failed."""

    def __init__(self) -> None:
        self._out = _console()
        self._err = _console(stderr=True)
        self.presented: Optional[UploadImageOutputDto] = None

    def present(self, output_dto: UploadImageOutputDto) -> None:
        self.presented = output_dto
        name = escape(output_dto.path.name)
        if not output_dto.success:
            self._err.print()
            self._err.print(f"[error]✗[/] [path]{name}[/]  [error]{escape(output_dto.error or 'failed')}[/]")
            return
        self._out.print()
        self._out.print(f"[ok]✓[/] [path]{name}[/] [summary]on azure[/]  [ok]uploaded[/]")
        self._out.print(f"  [field]image[/]  {output_dto.image_name}")
        self._out.print(f"  [field]group[/]  {output_dto.resource_group}")
        self._out.print(f"  [field]id[/]     {output_dto.image_id}")


class CliProvisionLog(ProvisionLog):
    """Print the provisioner's live output dimmed, so the result stands out after it."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self._console = console if console is not None else _console()

    def line(self, text: str) -> None:
        self._console.print(f"[summary]{escape(text)}[/]")


class CliProvisionPresenter(ProvisionOutputBoundary):
    """Print the result of plan, build, or destroy and keep the presented value."""

    def __init__(self) -> None:
        self._out = _console()
        self._err = _console(stderr=True)
        self._presented: Optional[ProvisionOutputDto] = None

    def present(self, dto: ProvisionOutputDto) -> None:
        self._presented = dto
        subject = escape(dto.cyber_range or str(dto.location or dto.range_id))
        provider = f" [summary]on {dto.provider}[/]" if dto.provider else ""
        range_id = f"\n  [field]id[/]     {dto.range_id}" if dto.range_id and dto.cyber_range else ""
        state = f"\n  [field]state[/]  {_state(dto.state)}" if dto.state else ""

        if not dto.success:
            self._err.print()
            self._err.print(
                f"[error]✗[/] [path]{subject}[/]{provider}  [error]{escape(dto.error or 'failed')}[/]{range_id}{state}"
            )
            _print_changes(self._err, dto.changes)
            return

        done = "unchanged" if dto.action == "update" and not dto.changes else _DONE[dto.action]
        self._out.print()
        self._out.print(f"[ok]✓[/] [path]{subject}[/]{provider}  [ok]{done}[/]{range_id}")
        _print_changes(self._out, dto.changes)
        servers = dto.outputs.get("servers")
        if dto.action == "build" and isinstance(servers, dict) and servers:
            self._out.print(_servers_table(servers))

    def get_presented_value(self) -> Optional[ProvisionOutputDto]:
        return self._presented


class CliListPresenter(ListRangesOutputBoundary):
    """Print the registered ranges as a table."""

    def __init__(self) -> None:
        self._out = _console()
        self._presented: Optional[ListRangesOutputDto] = None

    def present(self, dto: ListRangesOutputDto) -> None:
        self._presented = dto
        if not dto.ranges:
            self._out.print("[summary]No cyber ranges. Create one with `attack-range build PATH`.[/]")
        else:
            table = Table(box=None, pad_edge=False, header_style="field")
            table.add_column("id", no_wrap=True, min_width=36)
            table.add_column("name")
            table.add_column("provider", no_wrap=True)
            table.add_column("location")
            table.add_column("state", no_wrap=True)
            table.add_column("updated", no_wrap=True)
            for record in dto.ranges:
                table.add_row(
                    str(record.id),
                    escape(record.name),
                    record.provider,
                    escape(record.location),
                    _state(record.state),
                    record.updated_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                )
            # Piped output keeps every column whole, so it can be grepped and parsed.
            out = self._out
            if not out.is_terminal:
                natural = Measurement.get(out, out.options.update_width(10_000), table).maximum
                out = _console(width=max(out.width, natural))
            out.print(table)
        if dto.hidden:
            noun = "range" if dto.hidden == 1 else "ranges"
            self._out.print(f"[summary]{dto.hidden} destroyed {noun} hidden; show them with --all.[/]")

    def get_presented_value(self) -> Optional[ListRangesOutputDto]:
        return self._presented


class CliGetPresenter(GetRangeOutputBoundary):
    """Print one range: its record, network, servers, and history."""

    def __init__(self) -> None:
        self._out = _console()
        self._err = _console(stderr=True)
        self._presented: Optional[GetRangeOutputDto] = None

    def present(self, dto: GetRangeOutputDto) -> None:
        self._presented = dto
        if not dto.success or dto.record is None:
            self._err.print(f"[error]✗[/] {dto.range_id}  [error]{escape(dto.error or 'not found')}[/]")
            return

        record = dto.record
        self._out.print(f"[path]{escape(record.name)}[/] [summary]on {record.provider}[/]  {_state(record.state)}")
        _field(self._out, "id", str(record.id))
        _field(self._out, "user", record.user_name or "-")
        _field(self._out, "location", record.location)
        _field(self._out, "source", record.source)
        _field(self._out, "local state", "yes" if record.local_state else "no")
        _field(self._out, "created", _when(record.created_at))
        _field(self._out, "updated", _when(record.updated_at))
        if record.error:
            _field(self._out, "error", record.error)
        _print_wireguard(self._out, record)
        if dto.documents_error:
            self._out.print(f"  [error]documents[/]  {escape(dto.documents_error)}")
        elif dto.cyber_range is not None:
            _print_network(self._out, dto.cyber_range)
            _print_range_servers(self._out, dto.cyber_range, record)
        _print_files(self._out, dto.files)
        _print_history(self._out, record)

    def get_presented_value(self) -> Optional[GetRangeOutputDto]:
        return self._presented


class CliPrunePresenter(PruneRangesOutputBoundary):
    """Mention deleted ranges on stderr, so the output of the command itself stays clean."""

    def __init__(self) -> None:
        self._err = _console(stderr=True)
        self._presented: Optional[PruneRangesOutputDto] = None

    def present(self, dto: PruneRangesOutputDto) -> None:
        self._presented = dto
        if dto.deleted:
            noun = "range" if len(dto.deleted) == 1 else "ranges"
            self._err.print(
                f"[summary]Deleted {len(dto.deleted)} {noun} destroyed more than {dto.older_than.days} days ago.[/]"
            )
        for range_id, reason in dto.failed.items():
            self._err.print(f"[error]Could not delete destroyed range {range_id}:[/] {escape(reason)}")

    def get_presented_value(self) -> Optional[PruneRangesOutputDto]:
        return self._presented


_STATE_STYLE = {
    RangeState.BUILT: "ok",
    RangeState.BUILD_FAILED: "error",
    RangeState.DESTROY_FAILED: "error",
    RangeState.DESTROYED: "summary",
}


def _field(console: Console, label: str, value: str) -> None:
    console.print(f"  [field]{label:<11}[/] {escape(value)}")


def _when(moment: Any) -> str:
    return moment.astimezone().strftime("%Y-%m-%d %H:%M")


def _print_wireguard(console: Console, record: RangeRecord) -> None:
    wireguard = record.outputs.get("wireguard")
    if not isinstance(wireguard, dict) or not wireguard.get("public_ip"):
        return
    console.print()
    console.print("[field]wireguard[/]")
    _field(console, "endpoint", f"{wireguard['public_ip']}:51820")
    if wireguard.get("client_config"):
        _field(console, "config", str(wireguard["client_config"]))


def _print_network(console: Console, cyber_range: CyberRange) -> None:
    network = cyber_range.network
    console.print()
    console.print(
        f"[field]network[/]  {escape(network.metadata.name)}  [summary]{network.spec.address_space.cidr}[/]"
    )
    table = Table(box=None, pad_edge=False, header_style="field")
    for column in ("segment", "zone", "cidr"):
        table.add_column(column)
    for segment in network.spec.segments:
        cidr = segment.cidr if segment.cidr is not None else network.spec.segment_cidrs()[segment.name]
        table.add_row(escape(segment.name), escape(segment.zone), str(cidr))
    _fit(console, table).print(table)
    if network.spec.gateways:
        described = ", ".join(_gateway(gateway) for gateway in network.spec.gateways)
        console.print(f"  [field]gateways[/]  {escape(described)}")
    if cyber_range.tags:
        tags = " ".join(f"{key}={value}" for key, value in sorted(cyber_range.tags.items()))
        console.print(f"  [field]tags[/]  {escape(tags)}")


def _gateway(gateway: Any) -> str:
    if gateway.type == "nat":
        served = ", ".join(gateway.serves)
        return f"{gateway.name} (nat) on {gateway.attach}, serves {served}"
    return f"{gateway.name} on {gateway.attach}"


def _print_range_servers(console: Console, cyber_range: CyberRange, record: RangeRecord) -> None:
    console.print()
    console.print("[field]servers[/]")
    table = Table(box=None, pad_edge=False, header_style="field")
    for column in ("server", "user", "machine", "private ip", "public ip", "interfaces"):
        table.add_column(column)
    for server in cyber_range.servers:
        private_ip, public_ip = _output_addresses(record.outputs, server.metadata.name)
        table.add_row(
            escape(server.metadata.name),
            escape(server.spec.access.username),
            escape(_machine(cyber_range.binding(server))),
            escape(private_ip),
            escape(public_ip),
            escape(_interfaces(server)),
        )
    _fit(console, table).print(table)


def _output_addresses(outputs: dict[str, Any], name: str) -> tuple[str, str]:
    servers = outputs.get("servers")
    entry = servers.get(name) if isinstance(servers, dict) else None
    if not isinstance(entry, dict):
        return "-", "-"
    return str(entry.get("private_ip") or "-"), str(entry.get("public_ip") or "-")


def _interfaces(server: Server) -> str:
    return ", ".join(
        f"{interface.name} {interface.segment} {interface.address}" for interface in server.spec.interfaces
    )


def _machine(binding: ServerBinding) -> str:
    spec = binding.spec
    if isinstance(spec, AwsServerBindingSpec):
        image = spec.aws.ami or spec.aws.ami_name_filter or ""
        return f"{spec.aws.instance_type}  {image}".strip()
    if isinstance(spec, AzureServerBindingSpec):
        if spec.azure.image is not None:
            image = spec.azure.image
            described = f"{image.publisher}:{image.offer}:{image.sku}:{image.version}"
        elif spec.azure.image_publisher is not None:
            described = f"{spec.azure.image_publisher}:{spec.azure.image_offer}:{spec.azure.image_sku}"
        else:
            described = spec.azure.image_id or ""
        return f"{spec.azure.size}  {described}".strip()
    if isinstance(spec, VmwareServerBindingSpec):
        parts = [spec.vmware.template]
        if spec.vmware.cpu is not None:
            parts.append(f"{spec.vmware.cpu} cpu")
        if spec.vmware.memory_mib is not None:
            parts.append(f"{spec.vmware.memory_mib} MiB")
        return "  ".join(parts)
    return ""


def _print_files(console: Console, files: tuple[Path, ...]) -> None:
    if not files:
        return
    root = Path(os.path.commonpath(path.parent for path in files))
    console.print()
    console.print(f"[field]files[/]  {escape(str(root))}")
    for path in files:
        console.print(f"  {escape(str(path.relative_to(root)))}")


def _print_history(console: Console, record: RangeRecord) -> None:
    console.print()
    console.print("[field]history[/]")
    for change in record.history:
        message = f"  [summary]{escape(change.message)}[/]" if change.message else ""
        console.print(f"  {_state(change.state)}  {_when(change.at)}{message}")


def _fit(console: Console, table: Table) -> Console:
    """Widen piped output so a table keeps every column on one line."""
    if console.is_terminal:
        return console
    natural = Measurement.get(console, console.options.update_width(10_000), table).maximum
    return _console(stderr=console.stderr, width=max(console.width, natural))


def _state(state: Optional[RangeState]) -> str:
    if state is None:
        return "-"
    style = _STATE_STYLE.get(state)
    return f"[{style}]{state}[/]" if style else str(state)


def _print_changes(console: Console, changes: tuple[Any, ...]) -> None:
    for change in changes:
        console.print(f"  [field]{change.action}[/]  {escape(change.kind)} {escape(change.name)}")
        for parameter in change.parameters:
            console.print(f"    [summary]{escape(parameter)}[/]")


def _servers_table(servers: dict[str, Any]) -> Table:
    table = Table(box=None, pad_edge=False, header_style="field")
    for column in ("server", "private ip", "public ip"):
        table.add_column(column)
    for name, addresses in sorted(servers.items()):
        addresses = addresses if isinstance(addresses, dict) else {}
        table.add_row(
            escape(name),
            escape(str(addresses.get("private_ip") or "-")),
            escape(str(addresses.get("public_ip") or "-")),
        )
    return table

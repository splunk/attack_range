from typing import Any, Optional

from rich.console import Console
from rich.markup import escape
from rich.measure import Measurement
from rich.table import Table
from rich.theme import Theme

from attack_range.application.provisioner import ProvisionLog
from attack_range.domain.value_objects.range_state import RangeState
from attack_range.use_cases.list_ranges import ListRangesOutputBoundary, ListRangesOutputDto
from attack_range.use_cases.provision import ProvisionOutputBoundary, ProvisionOutputDto

_THEME = Theme(
    {
        "error": "bold red",
        "ok": "bold green",
        "path": "bold cyan",
        "field": "bold",
        "summary": "dim",
    }
)

_DONE = {"plan": "planned", "build": "built", "destroy": "destroyed"}


def _console(stderr: bool = False, width: Optional[int] = None) -> Console:
    return Console(stderr=stderr, width=width, theme=_THEME, soft_wrap=True, highlight=False, emoji=False)


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
            return

        self._out.print()
        self._out.print(f"[ok]✓[/] [path]{subject}[/]{provider}  [ok]{_DONE[dto.action]}[/]{range_id}")
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


_STATE_STYLE = {
    RangeState.BUILT: "ok",
    RangeState.BUILD_FAILED: "error",
    RangeState.DESTROY_FAILED: "error",
    RangeState.DESTROYED: "summary",
}


def _state(state: Optional[RangeState]) -> str:
    if state is None:
        return "-"
    style = _STATE_STYLE.get(state)
    return f"[{style}]{state}[/]" if style else str(state)


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

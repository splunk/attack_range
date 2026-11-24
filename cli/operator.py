"""CLI implementation of the operator port."""

import select
import sys
import termios
from pathlib import Path
from typing import Optional, TextIO

from rich.console import Console

from attack_range.application.operator import HangChoice, Operator
from attack_range.application.provisioner import ProvisionerError


class CliOperator(Operator):
    """Prints the WireGuard client configuration and waits until the operator continues."""

    def __init__(self) -> None:
        self._out = Console(soft_wrap=True, highlight=False, emoji=False)

    def connect_vpn(self, config: str) -> None:
        self._out.print()
        self._out.print("[bold]WireGuard[/]")
        self._out.print(config, markup=False, highlight=False)
        self._out.print("Copy this configuration into the WireGuard app and enable the tunnel.")
        self._out.print("Press Enter when the VPN is connected.")
        if not sys.stdin.isatty():
            raise ProvisionerError("enabling the WireGuard VPN needs a terminal")
        input()

    def confirm_vpn(self, path: Path) -> None:
        self._out.print()
        self._out.print("[bold]WireGuard[/]")
        self._out.print(f"The existing tunnel is not connected. Enable {path}.")
        self._out.print("Press Enter when the VPN is connected.")
        if not sys.stdin.isatty():
            raise ProvisionerError("checking the WireGuard VPN needs a terminal")
        input()

    def hung_command(self, title: str, idle_seconds: int, last_line: str, output: int) -> HangChoice:
        if not sys.stdin.isatty():
            raise ProvisionerError(f"{title} hung and there is no terminal to choose a retry")
        return self._choose(title, idle_seconds, last_line, sys.stdin, output)

    def _choose(
        self, title: str, idle_seconds: int, last_line: str, stdin: TextIO, output: int
    ) -> HangChoice:
        """Wait for an answer. The command keeps running and can close this prompt."""
        rows = self._show_hang(title, idle_seconds, last_line)
        while True:
            ready, _, _ = select.select([stdin, output], [], [])
            if stdin in ready:
                answer = stdin.readline()
                if not answer:
                    return HangChoice.ABORT
                choice = _hang_choice(answer)
                if choice is not None:
                    return choice
                notice = "Type r to retry, w to keep waiting, or a to abort."
                self._out.print(notice)
                rows += self._rows(notice) + 1
                continue
            self._clear(rows)
            if stdin.isatty():
                termios.tcflush(stdin.fileno(), termios.TCIFLUSH)
            return HangChoice.CONTINUE

    def _show_hang(self, title: str, idle_seconds: int, last_line: str) -> int:
        rows = 1
        self._out.print()
        summary = f"{title} has produced no output for {idle_seconds}s."
        self._out.print(f"[bold]{title}[/] has produced no output for {idle_seconds}s.")
        rows += self._rows(summary)
        if last_line:
            self._out.print(last_line, markup=False, highlight=False)
            rows += self._rows(last_line)
        instruction = "Type r and Enter to retry the step, w and Enter to keep waiting, or a and Enter to abort."
        self._out.print(instruction)
        rows += self._rows(instruction)
        note = "If it prints again before you answer, the build continues."
        self._out.print(note)
        rows += self._rows(note)
        return rows

    def _rows(self, text: str) -> int:
        width = max(1, self._out.width)
        return max(1, (len(text) + width - 1) // width)

    def _clear(self, rows: int) -> None:
        """Erase the prompt, including a partial answer on the current line."""
        file = self._out.file
        file.write("\r\033[K" + ("\033[1A\033[K" * rows))
        file.flush()


def _hang_choice(answer: str) -> Optional[HangChoice]:
    answer = answer.strip().lower()
    if answer in {"r", "retry"}:
        return HangChoice.RETRY
    if answer in {"w", "wait"}:
        return HangChoice.WAIT
    if answer in {"a", "abort"}:
        return HangChoice.ABORT
    return None

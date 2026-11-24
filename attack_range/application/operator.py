"""Port for the person running a build. The CLI implements the prompt."""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path


class HangChoice(Enum):
    """What to do when a provisioning command stops producing output."""

    RETRY = "retry"
    WAIT = "wait"
    ABORT = "abort"
    CONTINUE = "continue"


class Operator(ABC):
    """Asks the operator to do something the build cannot do itself."""

    @abstractmethod
    def connect_vpn(self, config: str) -> None:
        """Show the WireGuard client configuration and wait until the tunnel is enabled."""

    @abstractmethod
    def confirm_vpn(self, path: Path) -> None:
        """The existing tunnel is down. Wait until the operator enables it."""

    @abstractmethod
    def hung_command(self, title: str, idle_seconds: int, last_line: str, output: int) -> HangChoice:
        """A command produced no output. Ask whether to retry it, keep waiting, or abort.

        The command keeps running. `output` is its stdout. Return CONTINUE, after
        removing the prompt, when the command prints again before the operator answers.
        """


class NullOperator(Operator):
    """Does not prompt. A hang aborts so an unattended run cannot wait forever."""

    def connect_vpn(self, config: str) -> None:
        return

    def confirm_vpn(self, path: Path) -> None:
        return

    def hung_command(self, title: str, idle_seconds: int, last_line: str, output: int) -> HangChoice:
        return HangChoice.ABORT

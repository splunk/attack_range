"""Provisioner port: turns a cyber range into infrastructure code and drives its lifecycle."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .cyber_range import CyberRange


class ProvisionerError(RuntimeError):
    """Raised when a provisioner cannot render or run its infrastructure code."""


@dataclass(frozen=True)
class ProvisionResult:
    """Outcome of one plan, apply, or destroy run."""

    success: bool
    output: str
    outputs: dict[str, Any] = field(default_factory=dict)


class ProvisionLog(ABC):
    """Driven port for the live output of a provisioner run.

    The CLI supplies a console adapter. Tests leave the default NullProvisionLog in place.
    """

    @abstractmethod
    def line(self, text: str) -> None:
        """Show one line of tool output, without its line ending."""


class NullProvisionLog(ProvisionLog):
    def line(self, text: str) -> None:
        return


class Provisioner(ABC):
    """Base for infrastructure-as-code backends such as Terraform or Bicep.

    Every lifecycle call renders the code first, so what runs always matches the documents.
    A cyber range without an id is only planned, never applied.
    """

    def __init__(self, log: Optional[ProvisionLog] = None) -> None:
        self.log = log or NullProvisionLog()

    @abstractmethod
    def render(self, cyber_range: CyberRange) -> Path:
        """Write the infrastructure code for the cyber range and return the directory that holds it."""

    @abstractmethod
    def plan(self, cyber_range: CyberRange) -> ProvisionResult:
        """Show the changes that apply would make."""

    @abstractmethod
    def apply(self, cyber_range: CyberRange) -> ProvisionResult:
        """Create or update the infrastructure of the cyber range."""

    @abstractmethod
    def destroy(self, cyber_range: CyberRange) -> ProvisionResult:
        """Remove all infrastructure of the cyber range."""

    @abstractmethod
    def clean(self, cyber_range: CyberRange) -> None:
        """Delete the generated code of a destroyed range. Remote state is kept."""

"""Output and the shared failure handling of the plan, build, and destroy use cases."""

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional
from uuid import UUID

from attack_range.application.range_store import RangeStore
from attack_range.domain.entities.common import Provider
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState

Action = Literal["plan", "build", "destroy", "update"]
ConfigAction = Literal["added", "modified", "removed"]


@dataclass(frozen=True)
class ConfigChange:
    """One document in an update: a new document, an existing one with changed parameters, or a removal."""

    kind: str
    name: str
    action: ConfigAction
    parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProvisionOutputDto:
    action: Action
    success: bool
    location: Optional[Path] = None
    range_id: Optional[UUID] = None
    cyber_range: Optional[str] = None
    provider: Optional[Provider] = None
    state: Optional[RangeState] = None
    output: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    changes: tuple[ConfigChange, ...] = ()


class ProvisionOutputBoundary(abc.ABC):
    @abc.abstractmethod
    def present(self, dto: ProvisionOutputDto) -> None:
        pass

    @abc.abstractmethod
    def get_presented_value(self) -> Any:
        pass


def record_failure(store: RangeStore, record: RangeRecord, failed: RangeState, message: str) -> RangeRecord:
    """Move a range into a failed state and store it."""
    record = record.transition(failed, message)
    store.update(record)
    return record


def interruption_message(error: BaseException) -> str:
    if isinstance(error, KeyboardInterrupt):
        return "interrupted"
    return f"stopped by {type(error).__name__}: {error}"

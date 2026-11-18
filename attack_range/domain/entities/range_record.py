"""Record of one registered cyber range: identity, where it came from, and its lifecycle."""

from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from attack_range.domain.value_objects.range_state import TRANSITIONS, RangeState

from .common import Provider


class InvalidTransition(ValueError):
    """Raised when a range is asked to move to a state its current state does not allow."""


def _now() -> datetime:
    return datetime.now(UTC)


class StateChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: RangeState
    at: datetime
    message: Optional[str] = None


class RangeRecord(BaseModel):
    """A cyber range built from a template. Change it only through `transition`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    name: str
    provider: Provider
    location: str
    source: str
    """The template path the documents were copied from."""
    local_state: bool = False
    state: RangeState
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    outputs: dict[str, Any] = Field(default_factory=dict)
    history: list[StateChange] = Field(default_factory=list)

    @classmethod
    def new(cls, name: str, provider: Provider, location: str, source: str, local_state: bool = False) -> "RangeRecord":
        """Register a range under a fresh id, in state `created`."""
        now = _now()
        return cls(
            id=uuid4(),
            name=name,
            provider=provider,
            location=location,
            source=source,
            local_state=local_state,
            state=RangeState.CREATED,
            created_at=now,
            updated_at=now,
            history=[StateChange(state=RangeState.CREATED, at=now)],
        )

    def can_transition(self, to: RangeState) -> bool:
        return to in TRANSITIONS[self.state]

    def transition(
        self, to: RangeState, message: Optional[str] = None, outputs: Optional[dict[str, Any]] = None
    ) -> "RangeRecord":
        """Return a copy in state `to`. `message` becomes the error of a failed state."""
        if not self.can_transition(to):
            raise InvalidTransition(f"range {self.id} is {self.state} and cannot become {to}")
        now = _now()
        failed = to in (RangeState.BUILD_FAILED, RangeState.DESTROY_FAILED)
        return self.model_copy(update={
            "state": to,
            "error": message if failed else None,
            "updated_at": now,
            "outputs": self.outputs if outputs is None else outputs,
            "history": [*self.history, StateChange(state=to, at=now, message=message)],
        })

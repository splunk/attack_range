"""Lifecycle states of a registered cyber range and the transitions between them."""

from enum import StrEnum


class RangeState(StrEnum):
    CREATED = "created"
    BUILDING = "building"
    BUILT = "built"
    BUILD_FAILED = "build_failed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"
    DESTROY_FAILED = "destroy_failed"


TRANSITIONS: dict[RangeState, frozenset[RangeState]] = {
    RangeState.CREATED: frozenset({RangeState.BUILDING, RangeState.BUILD_FAILED}),
    RangeState.BUILDING: frozenset({RangeState.BUILT, RangeState.BUILD_FAILED}),
    RangeState.BUILT: frozenset({RangeState.BUILDING, RangeState.DESTROYING}),
    RangeState.BUILD_FAILED: frozenset({RangeState.BUILDING, RangeState.DESTROYING}),
    RangeState.DESTROYING: frozenset({RangeState.DESTROYED, RangeState.DESTROY_FAILED}),
    RangeState.DESTROY_FAILED: frozenset({RangeState.DESTROYING}),
    RangeState.DESTROYED: frozenset(),
}
"""States each state may move to. `destroyed` is final."""

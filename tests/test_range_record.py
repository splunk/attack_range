import pytest

from attack_range.domain.entities.range_record import InvalidTransition, RangeRecord
from attack_range.domain.value_objects.range_state import TRANSITIONS, RangeState


def new_record() -> RangeRecord:
    return RangeRecord.new(name="ar", provider="aws", location="eu-central-1", source="/ranges/ar")


def test_new_record_is_created() -> None:
    record = new_record()

    assert record.state is RangeState.CREATED
    assert [change.state for change in record.history] == [RangeState.CREATED]
    assert record.created_at == record.updated_at
    assert new_record().id != record.id


def test_every_state_has_transitions() -> None:
    assert set(TRANSITIONS) == set(RangeState)
    assert TRANSITIONS[RangeState.DESTROYED] == frozenset()


def test_build_and_destroy_lifecycle() -> None:
    record = new_record().transition(RangeState.BUILDING)
    record = record.transition(RangeState.BUILT, outputs={"servers": {"win": {}}})
    record = record.transition(RangeState.DESTROYING)

    assert record.outputs == {"servers": {"win": {}}}
    record = record.transition(RangeState.DESTROYED, outputs={})

    assert record.outputs == {}
    assert [change.state for change in record.history] == [
        RangeState.CREATED, RangeState.BUILDING, RangeState.BUILT, RangeState.DESTROYING, RangeState.DESTROYED,
    ]
    assert record.updated_at >= record.created_at


def test_transition_returns_a_new_record() -> None:
    record = new_record()

    building = record.transition(RangeState.BUILDING)

    assert record.state is RangeState.CREATED
    assert building.state is RangeState.BUILDING


def test_failure_keeps_error_until_next_transition() -> None:
    failed = new_record().transition(RangeState.BUILDING).transition(RangeState.BUILD_FAILED, "no credentials")

    assert failed.error == "no credentials"
    assert failed.history[-1].message == "no credentials"
    assert failed.transition(RangeState.BUILDING).error is None


@pytest.mark.parametrize(
    ("path", "target"),
    [
        ([], RangeState.BUILT),
        ([], RangeState.DESTROYING),
        ([RangeState.BUILDING, RangeState.BUILT, RangeState.DESTROYING, RangeState.DESTROYED], RangeState.BUILDING),
        ([RangeState.BUILDING], RangeState.DESTROYING),
    ],
)
def test_invalid_transitions(path: list[RangeState], target: RangeState) -> None:
    record = new_record()
    for state in path:
        record = record.transition(state)

    assert not record.can_transition(target)
    with pytest.raises(InvalidTransition, match=f"is {record.state} and cannot become {target}"):
        record.transition(target)


def test_round_trips_through_json() -> None:
    record = new_record().transition(RangeState.BUILDING).transition(RangeState.BUILD_FAILED, "boom")

    assert RangeRecord.model_validate(record.model_dump(mode="json")) == record

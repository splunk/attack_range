import sys

from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState
from attack_range_infrastructure.storage import AttackRangeHome, UserConfigError, YamlRangeStore, reset_user_config


def init_action() -> int:
    """Ask for a user name and password and store them in the home folder.

    A built range keeps the user name it was built with, so this is refused until
    every built range has been destroyed.
    """
    home = AttackRangeHome().ensure()
    built = [record for record in YamlRangeStore(home).list() if record.state is RangeState.BUILT]
    if built:
        print(_built_message(built), file=sys.stderr)
        return 1
    try:
        config = reset_user_config(home)
    except UserConfigError as error:
        print(error, file=sys.stderr)
        return 2
    print(f"Stored user name {config.user_name} in {home.config_file}")
    return 0


def _built_message(built: list[RangeRecord]) -> str:
    listed = ", ".join(f"{record.name} ({record.id})" for record in built)
    if len(built) == 1:
        return f"Cannot replace the user name and password while {listed} is built. Destroy it first."
    return (
        f"Cannot replace the user name and password while these ranges are built: {listed}. "
        "Destroy them first."
    )

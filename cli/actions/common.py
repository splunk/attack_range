import sys
from typing import Any

from attack_range.use_cases.prune_ranges import PruneRangesInputDto
from attack_range_infrastructure.storage import UserConfigError, ensure_user_config
from cli.container import Container


def open_container(**config: Any) -> Container:
    """Wire the container and delete ranges that were destroyed long enough ago.

    The first run asks for a user name and a password and stores them in the home folder.
    """
    container = Container()
    container.config.from_dict({"home": None, **config})
    try:
        ensure_user_config(container.home())
    except UserConfigError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from error
    container.prune_factory().execute(PruneRangesInputDto())
    return container

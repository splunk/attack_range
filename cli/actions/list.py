from attack_range.use_cases.list_ranges import ListRangesInputDto
from cli.container import Container


def list_action(include_destroyed: bool) -> int:
    """Print the registered ranges and return the exit code."""
    container = Container()
    container.config.from_dict({"home": None})
    container.list_factory().execute(ListRangesInputDto(include_destroyed=include_destroyed))
    return 0

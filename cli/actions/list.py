from attack_range.use_cases.list_ranges import ListRangesInputDto
from cli.actions.common import open_container


def list_action(include_destroyed: bool) -> int:
    """Print the registered ranges and return the exit code."""
    container = open_container()
    container.list_factory().execute(ListRangesInputDto(include_destroyed=include_destroyed))
    return 0

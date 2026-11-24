from uuid import UUID

from attack_range.use_cases.get_range import GetRangeInputDto
from cli.actions.common import open_container


def get_action(range_id: UUID) -> int:
    """Print one range and return the exit code."""
    container = open_container()
    container.get_factory().execute(GetRangeInputDto(range_id=range_id))
    presented = container.get_output_boundary().get_presented_value()
    return 0 if presented is not None and presented.success else 1

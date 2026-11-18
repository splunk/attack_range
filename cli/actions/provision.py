from pathlib import Path
from typing import Callable, Optional
from uuid import UUID

from attack_range.application.range_store import RangeNotFound
from attack_range.domain.entities.common import Provider
from attack_range.use_cases.build import BuildInputDto
from attack_range.use_cases.destroy import DestroyInputDto
from attack_range.use_cases.plan import PlanInputDto
from cli.container import Container


def plan_action(location: Path, provider: Optional[Provider], terraform_bin: str) -> int:
    """Plan the template at `location` without registering it and return the exit code."""
    container = _container(terraform_bin)
    container.plan_factory().execute(PlanInputDto(location=location, provider=provider))
    return _exit_code(container)


def build_action(location: Path, provider: Optional[Provider], local_state: bool, terraform_bin: str) -> int:
    """Register the template at `location` as a new range, build it, and return the exit code."""
    container = _container(terraform_bin)
    container.build_factory().execute(
        BuildInputDto(location=location, provider=provider, local_state=local_state)
    )
    return _exit_code(container)


def destroy_action(range_id: UUID, terraform_bin: str, confirm: Optional[Callable[[str], bool]] = None) -> int:
    """Destroy the registered range `range_id` and return the exit code.

    `confirm` gets a description of the range and returns whether to go on. Without it, the
    range is destroyed right away.
    """
    container = _container(terraform_bin)
    if confirm is not None and not confirm(_describe(container, range_id)):
        return 1
    container.destroy_factory().execute(DestroyInputDto(range_id=range_id))
    return _exit_code(container)


def _container(terraform_bin: str) -> Container:
    container = Container()
    container.config.from_dict({"home": None, "terraform_bin": terraform_bin})
    return container


def _describe(container: Container, range_id: UUID) -> str:
    try:
        record = container.range_store().get(range_id)
    except (RangeNotFound, ValueError):
        return str(range_id)
    return f"{record.name} on {record.provider} ({range_id})"


def _exit_code(container: Container) -> int:
    presented = container.output_boundary().get_presented_value()
    return 0 if presented is not None and presented.success else 1

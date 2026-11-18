from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from attr import define

from attack_range.application.cyber_range import CyberRangeError
from attack_range.application.provisioner import Provisioner, ProvisionerError
from attack_range.application.repository import CyberRangeRepository
from attack_range.domain.entities.common import Provider

from .provision import ProvisionOutputBoundary, ProvisionOutputDto


@dataclass(frozen=True)
class PlanInputDto:
    """A template file or directory. Without a provider, the documents must bind exactly one."""

    location: Path
    provider: Optional[Provider] = None


@define
class Plan:
    """Show what building the template would create. Nothing is registered."""

    _output_boundary: ProvisionOutputBoundary
    _repository: CyberRangeRepository
    _provisioner: Provisioner

    def execute(self, input_dto: PlanInputDto) -> None:
        try:
            cyber_range = self._repository.load(input_dto.location, input_dto.provider)
        except CyberRangeError as error:
            self._output_boundary.present(ProvisionOutputDto(
                action="plan", success=False, location=input_dto.location,
                provider=input_dto.provider, error=str(error),
            ))
            return

        try:
            result = self._provisioner.plan(cyber_range)
        except ProvisionerError as error:
            self._output_boundary.present(ProvisionOutputDto(
                action="plan", success=False, location=input_dto.location,
                cyber_range=cyber_range.name, provider=cyber_range.provider, error=str(error),
            ))
            return

        self._output_boundary.present(ProvisionOutputDto(
            action="plan",
            success=result.success,
            location=input_dto.location,
            cyber_range=cyber_range.name,
            provider=cyber_range.provider,
            output=result.output,
            error=None if result.success else "plan failed",
        ))

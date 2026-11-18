import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from attr import define

from attack_range.application.cyber_range import CyberRangeError
from attack_range.application.provisioner import Provisioner, ProvisionerError
from attack_range.application.range_documents import RangeDocuments
from attack_range.application.range_store import RangeStore
from attack_range.application.repository import CyberRangeRepository
from attack_range.domain.entities.common import Provider
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState

from .provision import ProvisionOutputBoundary, ProvisionOutputDto, interruption_message, record_failure


@dataclass(frozen=True)
class BuildInputDto:
    """A template file or directory. Without a provider, the documents must bind exactly one."""

    location: Path
    provider: Optional[Provider] = None
    local_state: bool = False


@define
class Build:
    """Register a new range from a template under a fresh id and create its infrastructure."""

    _output_boundary: ProvisionOutputBoundary
    _repository: CyberRangeRepository
    _documents: RangeDocuments
    _store: RangeStore
    _provisioner: Provisioner

    def execute(self, input_dto: BuildInputDto) -> None:
        try:
            template = self._repository.load(input_dto.location, input_dto.provider)
        except CyberRangeError as error:
            self._output_boundary.present(ProvisionOutputDto(
                action="build", success=False, location=input_dto.location,
                provider=input_dto.provider, error=str(error),
            ))
            return

        record = RangeRecord.new(
            name=template.name,
            provider=template.provider,
            location=template.location,
            source=str(Path(input_dto.location).resolve()),
            local_state=input_dto.local_state,
        )
        self._store.create(record)

        try:
            self._documents.import_documents(record.id, input_dto.location)
            cyber_range = self._documents.load(record.id, record.provider)
        except (CyberRangeError, OSError, ValueError) as error:
            self._present(input_dto, record_failure(self._store, record, RangeState.BUILD_FAILED, str(error)))
            return
        cyber_range = dataclasses.replace(cyber_range, local_state=record.local_state)

        record = record.transition(RangeState.BUILDING)
        self._store.update(record)
        try:
            result = self._provisioner.apply(cyber_range)
        except ProvisionerError as error:
            self._present(input_dto, record_failure(self._store, record, RangeState.BUILD_FAILED, str(error)))
            return
        except BaseException as error:
            record_failure(self._store, record, RangeState.BUILD_FAILED, interruption_message(error))
            raise

        if result.success:
            record = record.transition(RangeState.BUILT, outputs=result.outputs)
            self._store.update(record)
        else:
            record = record_failure(self._store, record, RangeState.BUILD_FAILED, "build failed")
        self._present(input_dto, record, output=result.output)

    def _present(self, input_dto: BuildInputDto, record: RangeRecord, output: str = "") -> None:
        self._output_boundary.present(ProvisionOutputDto(
            action="build",
            success=record.state is RangeState.BUILT,
            location=input_dto.location,
            range_id=record.id,
            cyber_range=record.name,
            provider=record.provider,
            state=record.state,
            output=output,
            outputs=record.outputs,
            error=record.error,
        ))

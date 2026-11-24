import dataclasses
from dataclasses import dataclass
from uuid import UUID

from attr import define

from attack_range.application.cyber_range import CyberRangeError
from attack_range.application.provisioner import Provisioner, ProvisionerError
from attack_range.application.range_documents import RangeDocuments
from attack_range.application.range_store import RangeNotFound, RangeStore
from attack_range.domain.entities.range_record import InvalidTransition, RangeRecord
from attack_range.domain.value_objects.range_state import RangeState

from .provision import ProvisionOutputBoundary, ProvisionOutputDto, interruption_message, record_failure


@dataclass(frozen=True)
class DestroyInputDto:
    range_id: UUID


@define
class Destroy:
    """Remove the infrastructure of a registered range. Its record is kept as `destroyed`."""

    _output_boundary: ProvisionOutputBoundary
    _documents: RangeDocuments
    _store: RangeStore
    _provisioner: Provisioner

    def execute(self, input_dto: DestroyInputDto) -> None:
        try:
            record = self._store.get(input_dto.range_id)
        except RangeNotFound as error:
            self._output_boundary.present(ProvisionOutputDto(
                action="destroy", success=False, range_id=input_dto.range_id, error=str(error),
            ))
            return

        try:
            record = record.transition(RangeState.DESTROYING)
        except InvalidTransition as error:
            self._present(record, error=str(error))
            return
        self._store.update(record)

        try:
            cyber_range = self._documents.load(record.id, record.provider)
            cyber_range = dataclasses.replace(
                cyber_range, local_state=record.local_state, user_name=record.user_name
            )
            result = self._provisioner.destroy(cyber_range)
        except (CyberRangeError, ProvisionerError) as error:
            self._present(record_failure(self._store, record, RangeState.DESTROY_FAILED, str(error)))
            return
        except BaseException as error:
            record_failure(self._store, record, RangeState.DESTROY_FAILED, interruption_message(error))
            raise

        if not result.success:
            self._present(record_failure(self._store, record, RangeState.DESTROY_FAILED, "destroy failed"), result.output)
            return
        record = record.transition(RangeState.DESTROYED, outputs={})
        self._store.update(record)
        self._provisioner.clean(cyber_range)
        self._present(record, result.output)

    def _present(self, record: RangeRecord, output: str = "", error: str | None = None) -> None:
        self._output_boundary.present(ProvisionOutputDto(
            action="destroy",
            success=error is None and record.state is RangeState.DESTROYED,
            range_id=record.id,
            cyber_range=record.name,
            provider=record.provider,
            state=record.state,
            output=output,
            error=error or record.error,
        ))

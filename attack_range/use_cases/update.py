"""Update a registered cyber range by adding documents or removing config files."""

import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Sequence
from uuid import UUID

from attr import define, field

from attack_range.application.cyber_range import CyberRange, CyberRangeError, Document, assemble_cyber_range
from attack_range.application.guest_provisioner import GuestProvisioner, NullGuestProvisioner
from attack_range.application.operator import NullOperator, Operator
from attack_range.application.overrides import DeployOverrides, override_documents, provider_location
from attack_range.application.provisioner import Provisioner, ProvisionerError
from attack_range.application.range_documents import RangeDocuments
from attack_range.application.range_store import RangeNotFound, RangeStore
from attack_range.application.repository import CyberRangeRepository
from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.entities.server import Server
from attack_range.domain.entities.server_binding import ServerBinding
from attack_range.domain.value_objects.range_state import RangeState

from .provision import (
    ConfigChange,
    ProvisionOutputBoundary,
    ProvisionOutputDto,
    interruption_message,
    record_failure,
)
from .provision_guests import provision_guests

_UPDATABLE = frozenset({RangeState.CREATED, RangeState.BUILT, RangeState.BUILD_FAILED})


@dataclass(frozen=True)
class UpdateInputDto:
    """An update of a registered range.

    `location` merges those documents in. With `mode` `change`, every document in that
    path must already be in the range. `files` removes those config files, named as
    `get` lists them. `sets` apply only when adding: each one replaces a field on the
    merged documents.
    """

    range_id: UUID
    location: Optional[Path] = None
    files: tuple[str, ...] = ()
    mode: Literal["add", "change"] = "add"
    sets: tuple = ()


@define
class Update:
    """Add documents, apply changes to existing ones, or remove config files.

    A document whose kind and name already exist is a parameter change. A document that
    does not exist yet is added, except by `change`, which rejects it. Documents the
    path does not mention stay as they are. Removing a server binding also removes its server.
    """

    _output_boundary: ProvisionOutputBoundary
    _repository: CyberRangeRepository
    _documents: RangeDocuments
    _store: RangeStore
    _provisioner: Provisioner
    _guests: GuestProvisioner = field(factory=NullGuestProvisioner)
    _operator: Operator = field(factory=NullOperator)

    def execute(self, input_dto: UpdateInputDto) -> None:
        try:
            record = self._store.get(input_dto.range_id)
        except RangeNotFound as error:
            self._present(input_dto, success=False, error=str(error))
            return
        if record.state not in _UPDATABLE:
            self._present(
                input_dto, record, success=False,
                error=f"range {record.id} is {record.state} and cannot be updated",
            )
            return

        try:
            existing, existing_files = self._documents.read(record.id)
            if input_dto.files:
                merged, files, changes = self._remove(record, existing, existing_files, input_dto.files)
            else:
                if input_dto.location is None:
                    raise CyberRangeError(f"update {input_dto.mode} needs a path")
                incoming, incoming_files = self._repository.read(input_dto.location)
                if input_dto.mode == "change":
                    _require_existing(existing, incoming)
                merged = merge(existing, incoming)
                if input_dto.mode == "add":
                    merged = override_documents(
                        merged, record.provider, DeployOverrides(sets=input_dto.sets)
                    )
                changes = classify(existing, merged)
                changes = _with_bootstrap_changes(changes, existing, existing_files, incoming_files)
                files = {**existing_files, **incoming_files}
        except (CyberRangeError, OSError, ValueError) as error:
            self._present(input_dto, record, success=False, error=str(error))
            return
        if not changes:
            self._present(input_dto, record, success=True, changes=())
            return

        try:
            assemble_cyber_range(merged, record.provider, files)
        except CyberRangeError as error:
            self._present(input_dto, record, success=False, error=str(error), changes=tuple(changes))
            return

        try:
            self._documents.replace(record.id, merged, files)
            cyber_range = self._documents.load(record.id, record.provider)
        except (CyberRangeError, OSError, ValueError) as error:
            self._present(input_dto, record, success=False, error=str(error), changes=tuple(changes))
            return
        cyber_range = dataclasses.replace(
            cyber_range, local_state=record.local_state, user_name=record.user_name
        )

        if input_dto.mode == "add" and input_dto.sets:
            location = provider_location(merged, record.provider)
            if location is not None:
                record = record.model_copy(update={"location": location})
        record = record.transition(RangeState.BUILDING)
        self._store.update(record)
        try:
            result = self._provisioner.apply(cyber_range)
        except ProvisionerError as error:
            self._present(
                input_dto,
                record_failure(self._store, record, RangeState.BUILD_FAILED, str(error)),
                success=False,
                error=str(error),
                changes=tuple(changes),
            )
            return
        except BaseException as error:
            record_failure(self._store, record, RangeState.BUILD_FAILED, interruption_message(error))
            raise

        if result.success:
            try:
                outputs = provision_guests(
                    cyber_range,
                    result.outputs,
                    self._guests,
                    self._operator,
                    reuse_vpn=True,
                    servers=servers_to_provision(changes, cyber_range),
                )
            except ProvisionerError as error:
                self._present(
                    input_dto,
                    record_failure(self._store, record, RangeState.BUILD_FAILED, str(error)),
                    success=False,
                    error=str(error),
                    changes=tuple(changes),
                )
                return
            except BaseException as error:
                record_failure(self._store, record, RangeState.BUILD_FAILED, interruption_message(error))
                raise
            record = record.transition(RangeState.BUILT, outputs=outputs)
            self._store.update(record)
            self._present(input_dto, record, success=True, output=result.output, changes=tuple(changes))
            return
        record = record_failure(self._store, record, RangeState.BUILD_FAILED, "update failed")
        self._present(
            input_dto, record, success=False, output=result.output, error=record.error, changes=tuple(changes)
        )

    def _remove(
        self,
        record: RangeRecord,
        existing: Sequence[Document],
        existing_files: dict[str, str],
        names: tuple[str, ...],
    ) -> tuple[list[Document], dict[str, str], list[ConfigChange]]:
        """Drop the named config files. A server binding leaves only with its server."""
        selected = _select_files(self._documents.paths(record.id), names)
        removed: list[Document] = []
        removed_data: set[str] = set()
        for path in selected:
            if path.parent.name == "user-data":
                removed_data.add(path.name)
            else:
                removed.extend(self._repository.read(path)[0])
        removed_ids = {_identity(document) for document in removed}
        current = {_identity(document): document for document in existing}
        missing = [document for document in removed if _identity(document) not in current]
        if missing:
            document = missing[0]
            raise CyberRangeError(f"{document.kind} '{document.metadata.name}' is not in the range")
        remaining = [document for document in existing if _identity(document) not in removed_ids]
        _require_server_removed_with_binding(removed, remaining, record.provider)
        files = dict(existing_files)
        for name in removed_data:
            users = _bootstrap_users(remaining, name)
            if users:
                raise CyberRangeError(f"user data '{name}' is still used by server '{users[0]}'")
            files.pop(name, None)
        referenced = {
            document.spec.bootstrap.user_data
            for document in remaining
            if isinstance(document, Server) and document.spec.bootstrap is not None
        }
        for name in list(files):
            if name not in referenced:
                files.pop(name)
        changes = [
            ConfigChange(kind=document.kind, name=document.metadata.name, action="removed")
            for document in removed
        ]
        if removed_data and not changes:
            raise CyberRangeError("removing a user-data file does not change the range")
        return remaining, files, changes

    def _present(
        self,
        input_dto: UpdateInputDto,
        record: Optional[RangeRecord] = None,
        success: bool = False,
        output: str = "",
        error: Optional[str] = None,
        changes: tuple[ConfigChange, ...] = (),
    ) -> None:
        self._output_boundary.present(ProvisionOutputDto(
            action="update",
            success=success,
            location=input_dto.location,
            range_id=input_dto.range_id,
            cyber_range=None if record is None else record.name,
            provider=None if record is None else record.provider,
            state=None if record is None else record.state,
            output=output,
            outputs={} if record is None else record.outputs,
            error=error,
            changes=changes,
        ))


def servers_to_provision(changes: Sequence[ConfigChange], cyber_range: CyberRange) -> set[str]:
    """Servers whose document or binding was added or modified. Removed servers are gone."""
    binding_servers = {
        binding.metadata.name: binding.spec.server for binding in cyber_range.server_bindings.values()
    }
    names: set[str] = set()
    for change in changes:
        if change.action == "removed":
            continue
        if change.kind == "Server":
            names.add(change.name)
        elif change.kind == "ServerBinding":
            server = binding_servers.get(change.name)
            if server is not None:
                names.add(server)
    return names


def _require_existing(existing: Sequence[Document], incoming: Sequence[Document]) -> None:
    """Reject a document that is not already in the range."""
    current = {_identity(document) for document in existing}
    for document in incoming:
        identity = _identity(document)
        if identity not in current:
            raise CyberRangeError(
                f"{identity[0]} '{identity[1]}' is not in the range. update add introduces a new document"
            )


def _select_files(available: Sequence[Path], names: tuple[str, ...]) -> list[Path]:
    """Resolve config file names to the files stored for the range."""
    if not names:
        raise CyberRangeError("update remove needs a config file")
    if not available:
        raise CyberRangeError(f"config file '{names[0]}' is not in the range")
    root = Path(os.path.commonpath(path.parent for path in available))
    seen: set[Path] = set()
    selected: list[Path] = []
    for name in names:
        token = name.strip().replace("\\", "/").removeprefix("./")
        if not token:
            raise CyberRangeError("config file name is empty")
        matches = [
            path for path in available
            if path.name == token or path.relative_to(root).as_posix() == token
        ]
        if not matches:
            raise CyberRangeError(f"config file '{token}' is not in the range")
        if len(matches) > 1:
            raise CyberRangeError(f"config file '{token}' matches more than one file")
        path = matches[0]
        if path in seen:
            raise CyberRangeError(f"config file '{token}' is listed more than once")
        seen.add(path)
        selected.append(path)
    return selected


def _require_server_removed_with_binding(
    removed: Sequence[Document], remaining: Sequence[Document], provider: str
) -> None:
    """A server binding is removed only together with the server it configures."""
    removed_servers = {document.metadata.name for document in removed if isinstance(document, Server)}
    for binding in removed:
        if not isinstance(binding, ServerBinding):
            continue
        if binding.spec.server not in removed_servers:
            raise CyberRangeError(
                f"server binding '{binding.metadata.name}' cannot be removed without server '{binding.spec.server}'"
            )
    for binding in remaining:
        if not isinstance(binding, ServerBinding) or binding.spec.provider != provider:
            continue
        if binding.spec.server in removed_servers:
            raise CyberRangeError(
                f"server '{binding.spec.server}' cannot be removed without server binding '{binding.metadata.name}'"
            )


def _bootstrap_users(documents: Sequence[Document], name: str) -> list[str]:
    return [
        document.metadata.name
        for document in documents
        if isinstance(document, Server)
        and document.spec.bootstrap is not None
        and document.spec.bootstrap.user_data == name
    ]


def _with_bootstrap_changes(
    changes: list[ConfigChange],
    existing: Sequence[Document],
    existing_files: dict[str, str],
    incoming_files: dict[str, str],
) -> list[ConfigChange]:
    """Treat a changed bootstrap script as a change to the server that names it."""
    changed = {(change.kind, change.name) for change in changes}
    extra: list[ConfigChange] = []
    for document in existing:
        if not isinstance(document, Server) or document.spec.bootstrap is None:
            continue
        name = document.spec.bootstrap.user_data
        if name not in incoming_files or existing_files.get(name) == incoming_files[name]:
            continue
        if ("Server", document.metadata.name) in changed:
            continue
        extra.append(ConfigChange(
            kind="Server", name=document.metadata.name, action="modified", parameters=("bootstrap.userData",)
        ))
    return [*changes, *extra]


def classify(existing: Sequence[Document], incoming: Sequence[Document]) -> list[ConfigChange]:
    """Tell added documents from existing documents whose parameters changed."""
    current = {_identity(document): document for document in existing}
    seen: set[tuple[str, str]] = set()
    changes: list[ConfigChange] = []
    for document in incoming:
        identity = _identity(document)
        if identity in seen:
            raise CyberRangeError(f"duplicate {identity[0]} '{identity[1]}'")
        seen.add(identity)
        previous = current.get(identity)
        if previous is None:
            changes.append(ConfigChange(kind=document.kind, name=document.metadata.name, action="added"))
            continue
        parameters = tuple(_diff(_dump(previous), _dump(document), ""))
        if parameters:
            changes.append(ConfigChange(
                kind=document.kind, name=document.metadata.name, action="modified", parameters=parameters
            ))
    return changes


def merge(existing: Sequence[Document], incoming: Sequence[Document]) -> list[Document]:
    """Return `existing` with incoming documents replacing matches and new documents appended."""
    incoming_by_id = {_identity(document): document for document in incoming}
    seen: set[tuple[str, str]] = set()
    merged: list[Document] = []
    for document in existing:
        identity = _identity(document)
        seen.add(identity)
        merged.append(incoming_by_id.get(identity, document))
    for document in incoming:
        if _identity(document) not in seen:
            merged.append(document)
    return merged


def _identity(document: Document) -> tuple[str, str]:
    return (document.kind, document.metadata.name)


def _dump(document: Document) -> dict[str, Any]:
    return document.model_dump(mode="json", by_alias=True, exclude_none=True)


def _diff(before: Any, after: Any, prefix: str) -> list[str]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                paths.append(child)
            else:
                paths.extend(_diff(before[key], after[key], child))
        return paths
    if isinstance(before, list) and isinstance(after, list):
        paths = []
        shared = min(len(before), len(after))
        for index in range(shared):
            paths.extend(_diff(before[index], after[index], f"{prefix}[{index}]"))
        for index in range(shared, max(len(before), len(after))):
            paths.append(f"{prefix}[{index}]")
        return paths
    return [prefix or "<root>"]

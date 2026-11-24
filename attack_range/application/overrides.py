"""Replace document fields for one plan, build, or update add."""

import dataclasses
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from pydantic import ValidationError
from pydantic.alias_generators import to_camel

from attack_range.application.cyber_range import CyberRange, CyberRangeError, Document, assemble_cyber_range
from attack_range.domain.entities import NetworkBinding
from attack_range.domain.entities.common import Provider


@dataclass(frozen=True)
class FieldOverride:
    """One field to replace. `target` is a document name, or `*` for every matching document."""

    target: str
    path: tuple[str, ...]
    value: Any


@dataclass(frozen=True)
class DeployOverrides:
    """Field replacements for this command. Documents that are not named stay as written."""

    sets: tuple[FieldOverride, ...] = ()

    @property
    def any(self) -> bool:
        return bool(self.sets)


def override_range(cyber_range: CyberRange, overrides: DeployOverrides) -> CyberRange:
    """Return the range with the overrides applied. Bindings of other providers stay out of the result."""
    if not overrides.any:
        return cyber_range
    documents = [
        cyber_range.network,
        cyber_range.network_binding,
        *cyber_range.servers,
        *cyber_range.server_bindings.values(),
    ]
    updated = assemble_cyber_range(
        override_documents(documents, cyber_range.provider, overrides),
        cyber_range.provider,
        cyber_range.bootstrap_files,
    )
    return dataclasses.replace(
        updated,
        id=cyber_range.id,
        user_name=cyber_range.user_name,
        local_state=cyber_range.local_state,
        ssh_public_key=cyber_range.ssh_public_key,
    )


def override_documents(
    documents: Sequence[Document], provider: Provider, overrides: DeployOverrides
) -> list[Document]:
    """Return every document, with each override written onto the documents it names.

    `*` matches documents of `provider`, and documents that name no provider, when they have the path.
    """
    if not overrides.any:
        return list(documents)
    selected = list(documents)
    for item in overrides.sets:
        matches = [document for document in selected if _matches(document, item, provider)]
        if not matches:
            where = item.target if item.target != "*" else provider
            raise CyberRangeError(f"no document '{where}' has {'.'.join(item.path)}")
        matched = {id(document) for document in matches}
        selected = [
            _apply(document, item) if id(document) in matched else document for document in selected
        ]
    return selected


def provider_location(documents: Sequence[Document], provider: Provider) -> Optional[str]:
    """Location of the network binding for `provider`, when the documents include one."""
    for document in documents:
        if isinstance(document, NetworkBinding) and document.spec.provider == provider:
            return document.spec.location
    return None


def _matches(document: Document, item: FieldOverride, provider: Provider) -> bool:
    if item.target == "*":
        return _provider_allows(document, provider) and _has_path(document, item.path)
    return document.metadata.name == item.target


def _provider_allows(document: Document, provider: Provider) -> bool:
    bound = getattr(document.spec, "provider", None)
    return bound is None or bound == provider


def _apply(document: Document, item: FieldOverride) -> Document:
    data = document.model_dump(mode="json")
    try:
        _assign(data, item.path, item.value)
    except KeyError as error:
        raise CyberRangeError(f"{document.metadata.name} has no {'.'.join(item.path)}") from error
    return _validate(type(document), data)


def _has_path(document: Document, path: tuple[str, ...]) -> bool:
    node: Any = document.model_dump(mode="json")
    for key in path:
        if not isinstance(node, dict):
            return False
        resolved = _key(node, key)
        if resolved is None:
            return False
        node = node[resolved]
    return True


def _assign(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    node = data
    for key in path[:-1]:
        resolved = _key(node, key)
        if resolved is None or not isinstance(node.get(resolved), dict):
            raise KeyError(key)
        node = node[resolved]
    resolved = _key(node, path[-1])
    if resolved is None:
        raise KeyError(path[-1])
    node[resolved] = value


def _key(node: dict[str, Any], key: str) -> Optional[str]:
    if key in node:
        return key
    camel = to_camel(key)
    if camel in node:
        return camel
    return None


def _validate(kind: type[Document], data: dict) -> Document:
    try:
        return kind.model_validate(data)
    except ValidationError as error:
        messages = [str(item["msg"]).removeprefix("Value error, ") for item in error.errors()]
        raise CyberRangeError("; ".join(messages)) from error

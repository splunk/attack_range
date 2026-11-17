"""Types shared by every v0.1 lab document."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel

Name = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")]
"""Name of a document, zone, segment, gateway, or filter."""

FileName = Annotated[str, StringConstraints(pattern=r"^[^/\\]+\.[^/\\.]+$")]
"""File name with an extension and no path separator."""

ApiVersion = Literal["v0.1"]
Provider = Literal["aws", "azure", "vmware"]


class SpecModel(BaseModel):
    """Base for all document objects. Keys are camelCase in YAML and unknown keys are invalid."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class Metadata(SpecModel):
    """Document metadata."""

    name: Name


def require_unique(kind: str, names: list[str]) -> None:
    """Raise when a name appears more than once in a list."""
    seen: set[str] = set()
    for name in names:
        if name in seen:
            raise ValueError(f"duplicate {kind} name '{name}'")
        seen.add(name)

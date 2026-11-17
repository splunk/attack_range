"""Pydantic models for the v0.1 lab documents: Network, NetworkBinding, Server, and ServerBinding."""

from typing import Annotated, Any, Union

from pydantic import Field, TypeAdapter

from .network import Network
from .network_binding import NetworkBinding
from .server import Server
from .server_binding import ServerBinding

AnyDocument = Annotated[Union[Network, NetworkBinding, Server, ServerBinding], Field(discriminator="kind")]

_document_adapter: TypeAdapter[AnyDocument] = TypeAdapter(AnyDocument)


def parse_document(data: Any) -> Union[Network, NetworkBinding, Server, ServerBinding]:
    """Validate one parsed YAML document and return the model for its `kind`."""
    return _document_adapter.validate_python(data)


__all__ = [
    "AnyDocument",
    "Network",
    "NetworkBinding",
    "Server",
    "ServerBinding",
    "parse_document",
]

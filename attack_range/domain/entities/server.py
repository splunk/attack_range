"""Server document: one guest attached to segments of a Network."""

from ipaddress import IPv4Address
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import AnyUrl, Field, StringConstraints, UrlConstraints, model_validator

from .common import ApiVersion, FileName, Metadata, Name, SpecModel, require_unique

PublicKey = Annotated[str, StringConstraints(pattern=r"^(ssh-|ecdsa-|sk-)\S+ \S+")]
RoleName = Annotated[str, StringConstraints(pattern=r"^[\w-]+(\.[\w-]+)?$")]
HttpsUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["https"])]


class Access(SpecModel):
    """Login identity for the guest. The document holds public keys only."""

    username: str = Field(min_length=1)
    authorized_keys: list[PublicKey] = Field(min_length=1)


class Interface(SpecModel):
    """Attachment of the server to one segment."""

    name: str = Field(min_length=1)
    segment: Name
    address: Union[Literal["auto"], IPv4Address]
    public: bool = False
    filters: list[Name] = Field(default_factory=list)


class Bootstrap(SpecModel):
    """Guest bootstrap file, read from tmp/user-data."""

    user_data: FileName


class AnsibleStep(SpecModel):
    """Runs one Ansible role against the guest."""

    type: Literal["ansible"]
    role: RoleName
    vars: dict[str, Any] = Field(default_factory=dict)


class LocalPythonStep(SpecModel):
    """Copies a script from tmp/python to the guest and runs it with python3."""

    type: Literal["python"]
    source: Literal["local"]
    file: FileName


class RemotePythonStep(SpecModel):
    """Downloads a script on the guest and runs it with python3."""

    type: Literal["python"]
    source: Literal["remote"]
    url: HttpsUrl


PythonStep = Annotated[Union[LocalPythonStep, RemotePythonStep], Field(discriminator="source")]
ProvisioningStep = Annotated[Union[AnsibleStep, PythonStep], Field(discriminator="type")]


class ServerSpec(SpecModel):
    """Body of a Server document."""

    network: Name
    access: Access
    interfaces: list[Interface] = Field(min_length=1)
    bootstrap: Optional[Bootstrap] = None
    provisioning: list[ProvisioningStep] = Field(default_factory=list)

    @property
    def primary_interface(self) -> Interface:
        """The first interface, which carries the default route."""
        return self.interfaces[0]

    @model_validator(mode="after")
    def _unique_interfaces(self) -> "ServerSpec":
        require_unique("interface", [interface.name for interface in self.interfaces])
        return self


class Server(SpecModel):
    """One guest that a ServerBinding realizes on a provider."""

    api_version: ApiVersion
    kind: Literal["Server"]
    metadata: Metadata
    spec: ServerSpec

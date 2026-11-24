"""Server document: one guest attached to segments of a Network."""

from ipaddress import IPv4Address
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import AnyUrl, Field, StringConstraints, UrlConstraints, model_validator

from .common import ApiVersion, FileName, Metadata, Name, SpecModel, require_unique

PublicKey = Annotated[str, StringConstraints(pattern=r"^(ssh-|ecdsa-|sk-)\S+ \S+")]
RoleName = Annotated[str, StringConstraints(pattern=r"^[\w-]+(\.[\w-]+)?$")]
HttpsUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["https"])]
Revision = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][\w.-]*$")]
GroupName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][\w.-]*$")]


class Winrm(SpecModel):
    """WinRM settings Ansible uses to provision a Windows guest."""

    port: int = Field(default=5985, ge=1, le=65535)
    scheme: Literal["http", "https"] = "http"
    transport: Literal["basic", "ntlm", "credssp", "kerberos"] = "basic"
    cert_validation: Literal["ignore", "validate"] = "ignore"
    timeout_seconds: int = Field(default=600, ge=1)


class Access(SpecModel):
    """How the provisioner logs in to the guest."""

    username: str = Field(min_length=1)
    password: Optional[str] = Field(default=None, min_length=1)
    """Login password. `$PASSWORD$` is replaced from the home config."""
    ssh_key: Optional[str] = Field(default=None, min_length=1)
    """Private key used for SSH. `range` is the key generated for the range."""
    winrm: Optional[Winrm] = None
    """Set when this guest is provisioned over WinRM. The connection then uses `password`."""
    authorized_keys: list[PublicKey] = Field(default_factory=list)
    """Extra public keys installed for this user. The range key is separate and is always installed."""

    @model_validator(mode="after")
    def _one_credential(self) -> "Access":
        if self.password is not None and self.ssh_key is not None:
            raise ValueError("access sets either password or sshKey")
        if self.password is None and self.ssh_key is None:
            self.ssh_key = "range"
        if self.winrm is not None and self.password is None:
            raise ValueError("winrm access uses a password")
        return self


class Interface(SpecModel):
    """Attachment of the server to one segment."""

    name: str = Field(min_length=1)
    segment: Name
    address: Union[Literal["auto"], IPv4Address]
    public: bool = False
    filters: list[Name] = Field(default_factory=list)


class Bootstrap(SpecModel):
    """Guest bootstrap file.

    When this block is omitted, `config/user_data/<server>.<provider>.*` is used when
    that file exists. A set name such as `win.ps1` uses `config/user_data/win.<provider>.ps1`
    when that file exists. Any other name is read from `user-data/` next to the template.
    """

    user_data: FileName


class AnsibleStep(SpecModel):
    """Runs one Ansible role against the guest.

    Without `repository`, `role` is installed from Ansible Galaxy. With `repository`,
    the provisioner clones that git repository and uses the role at `rolePath`
    (the repository root when `rolePath` is omitted).
    """

    type: Literal["ansible"]
    role: RoleName
    repository: Optional[HttpsUrl] = None
    """Git repository cloned instead of installing `role` from Ansible Galaxy."""
    revision: Optional[Revision] = None
    """Branch or tag to clone. Requires `repository`."""
    role_path: Optional[str] = None
    """Directory of the role inside `repository`."""
    groups: list[GroupName] = Field(default_factory=list)
    """Inventory groups this guest joins before the role runs."""
    collections: list[RoleName] = Field(default_factory=list)
    """Ansible collections installed before the role."""
    environment: dict[str, str] = Field(default_factory=dict)
    """Environment variables for this role, including tasks delegated to localhost."""
    vars: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _repository_fields(self) -> "AnsibleStep":
        if self.repository is None and (self.revision is not None or self.role_path is not None):
            raise ValueError("revision and rolePath require repository")
        if self.role_path is not None:
            path = PurePosixPath(self.role_path)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("rolePath is a relative path inside the repository")
        if any(group in {"all", "ungrouped"} for group in self.groups):
            raise ValueError("groups cannot be all or ungrouped")
        if any(not key.isidentifier() or not value for key, value in self.environment.items()):
            raise ValueError("environment keys are identifiers and values are non-empty")
        require_unique("group", list(self.groups))
        require_unique("collection", list(self.collections))
        return self


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

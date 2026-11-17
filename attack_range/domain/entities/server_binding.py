"""ServerBinding document: realizes one Server on AWS, Azure, or VMware."""

from ipaddress import IPv4Address
from typing import Annotated, Literal, Optional, Union

from pydantic import Field, StringConstraints, model_validator

from .common import ApiVersion, Metadata, Name, SpecModel

AmiId = Annotated[str, StringConstraints(pattern=r"^ami-[0-9a-f]+$")]


class AwsServerRealize(SpecModel):
    """AWS resource kinds for the server functions."""

    server: Literal["instance"]
    interface: Literal["network-interface"]
    public: Optional[Literal["elastic-ip"]] = None


class AwsRootVolume(SpecModel):
    """EBS root volume."""

    size_gib: int = Field(gt=0, alias="sizeGiB")
    type: str = Field(min_length=1)


class AwsServerSettings(SpecModel):
    """EC2 machine settings."""

    instance_type: str = Field(min_length=1)
    ami: AmiId
    key_name: str = Field(min_length=1)
    root_volume: AwsRootVolume
    iam_instance_profile: Optional[str] = None
    security_group_names: Optional[list[str]] = None


class AwsServerBindingSpec(SpecModel):
    """ServerBinding body for AWS."""

    server: Name
    provider: Literal["aws"]
    location: str = Field(min_length=1)
    realize: AwsServerRealize
    aws: AwsServerSettings


class AzureServerRealize(SpecModel):
    """Azure resource kinds for the server functions."""

    server: Literal["virtual-machine"]
    interface: Literal["network-interface"]
    public: Optional[Literal["public-ip"]] = None


class AzureImage(SpecModel):
    """Marketplace image reference."""

    publisher: str = Field(min_length=1)
    offer: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    version: str = Field(min_length=1)


class AzureOsDisk(SpecModel):
    """Managed OS disk."""

    size_gib: int = Field(gt=0, alias="sizeGiB")
    storage_account_type: str = Field(min_length=1)


class AzureServerSettings(SpecModel):
    """Azure VM settings. Set exactly one of `image` or `imageId`."""

    resource_group: Optional[str] = None
    size: str = Field(min_length=1)
    image: Optional[AzureImage] = None
    image_id: Optional[str] = None
    os_disk: AzureOsDisk
    zone: Optional[str] = None
    admin_password_secret: Optional[str] = None
    network_security_group: Optional[str] = None

    @model_validator(mode="after")
    def _image_or_image_id(self) -> "AzureServerSettings":
        if (self.image is None) == (self.image_id is None):
            raise ValueError("azure sets exactly one of image or imageId")
        return self


class AzureServerBindingSpec(SpecModel):
    """ServerBinding body for Azure."""

    server: Name
    provider: Literal["azure"]
    location: str = Field(min_length=1)
    realize: AzureServerRealize
    azure: AzureServerSettings


class VmwareServerRealize(SpecModel):
    """VMware resource kinds. vSphere has no public-address resource."""

    server: Literal["virtual-machine"]
    interface: Literal["nic"]


class VmwareDisk(SpecModel):
    """System disk."""

    size_gib: Optional[int] = Field(None, gt=0, alias="sizeGiB")


class VmwareServerSettings(SpecModel):
    """vSphere machine settings. Set exactly one of `cluster` or `host`."""

    datacenter: Optional[str] = None
    cluster: Optional[str] = None
    host: Optional[str] = None
    datastore: str = Field(min_length=1)
    template: str = Field(min_length=1)
    folder: Optional[str] = None
    cpu: Optional[int] = Field(None, gt=0)
    memory_mib: Optional[int] = Field(None, gt=0, alias="memoryMiB")
    disk: Optional[VmwareDisk] = None
    dns: Optional[list[IPv4Address]] = None

    @model_validator(mode="after")
    def _cluster_or_host(self) -> "VmwareServerSettings":
        if (self.cluster is None) == (self.host is None):
            raise ValueError("vmware sets exactly one of cluster or host")
        return self


class VmwareServerBindingSpec(SpecModel):
    """ServerBinding body for VMware."""

    server: Name
    provider: Literal["vmware"]
    location: str = Field(min_length=1)
    realize: VmwareServerRealize
    vmware: VmwareServerSettings


ServerBindingSpec = Annotated[
    Union[AwsServerBindingSpec, AzureServerBindingSpec, VmwareServerBindingSpec],
    Field(discriminator="provider"),
]


class ServerBinding(SpecModel):
    """Realizes one Server on one provider."""

    api_version: ApiVersion
    kind: Literal["ServerBinding"]
    metadata: Metadata
    spec: ServerBindingSpec

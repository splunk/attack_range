"""NetworkBinding document: realizes one Network on AWS, Azure, or VMware."""

from typing import Annotated, Literal, Optional, Union

from pydantic import AfterValidator, Field, StringConstraints, field_validator

from .common import ApiVersion, Metadata, Name, SpecModel

RESERVED_TAGS = ("Name", "attack-range")
"""Tag keys the renderers set on every resource."""
_FORBIDDEN_TAG_CHARACTERS = set("<>%&\\?/")


def _check_tag_key(key: str) -> str:
    if key.lower().startswith(("aws:", "azure")):
        raise ValueError(f"tag key '{key}' uses a prefix reserved by the cloud provider")
    if forbidden := sorted(_FORBIDDEN_TAG_CHARACTERS.intersection(key)):
        raise ValueError(f"tag key '{key}' contains {' '.join(forbidden)}")
    if key in RESERVED_TAGS:
        raise ValueError(f"tag key '{key}' is set by attack range")
    return key


TagKey = Annotated[str, StringConstraints(min_length=1, max_length=128), AfterValidator(_check_tag_key)]
TagValue = Annotated[str, StringConstraints(max_length=256)]
Tags = dict[TagKey, TagValue]
"""Tags for every resource of the range. Keys follow the rules that AWS and Azure share."""


class AwsNetworkRealize(SpecModel):
    """AWS resource kinds for the network functions."""

    network: Literal["vpc"]
    segment: Literal["subnet"]
    internet: Optional[Literal["internet-gateway"]] = None
    nat: Optional[Literal["nat-gateway"]] = None
    filter: Optional[Literal["security-group"]] = None


class AwsNetworkBindingSpec(SpecModel):
    """NetworkBinding body for AWS. Subnets are placed in the first zone of `location`."""

    network: Name
    provider: Literal["aws"]
    location: str = Field(min_length=1)
    tags: Tags = Field(default_factory=dict)
    realize: AwsNetworkRealize


class AzureNetworkRealize(SpecModel):
    """Azure resource kinds for the network functions. Azure has no internet-gateway resource."""

    network: Literal["virtual-network"]
    segment: Literal["subnet"]
    nat: Optional[Literal["nat-gateway"]] = None
    filter: Optional[Literal["network-security-group"]] = None


class AzureNetworkSettings(SpecModel):
    """Azure resource group that holds the virtual network."""

    resource_group: str = Field(min_length=1)


class AzureNetworkBindingSpec(SpecModel):
    """NetworkBinding body for Azure."""

    network: Name
    provider: Literal["azure"]
    location: str = Field(min_length=1)
    tags: Tags = Field(default_factory=dict)
    realize: AzureNetworkRealize
    azure: AzureNetworkSettings


class VmwareNetworkRealize(SpecModel):
    """VMware mapping. v0.1 maps segments onto existing port groups and emits no network objects."""

    network: Literal["existing"]
    segment: Literal["port-group"]
    internet: Optional[Literal["existing"]] = None
    nat: Optional[Literal["existing"]] = None
    filter: Optional[Literal["existing"]] = None


class VmwarePortGroup(SpecModel):
    """Existing port group for one segment."""

    port_group: str = Field(min_length=1)


class VmwareNetworkSettings(SpecModel):
    """Datacenter and the port group of every segment."""

    datacenter: str = Field(min_length=1)
    segments: dict[Name, VmwarePortGroup] = Field(min_length=1)


class VmwareNetworkBindingSpec(SpecModel):
    """NetworkBinding body for VMware."""

    network: Name
    provider: Literal["vmware"]
    location: str = Field(min_length=1)
    tags: Tags = Field(default_factory=dict)
    realize: VmwareNetworkRealize
    vmware: VmwareNetworkSettings

    @field_validator("tags")
    @classmethod
    def _no_tags(cls, tags: Tags) -> Tags:
        if tags:
            raise ValueError("VMware bindings do not support tags in v0.1")
        return tags


NetworkBindingSpec = Annotated[
    Union[AwsNetworkBindingSpec, AzureNetworkBindingSpec, VmwareNetworkBindingSpec],
    Field(discriminator="provider"),
]


class NetworkBinding(SpecModel):
    """Realizes one Network on one provider."""

    api_version: ApiVersion
    kind: Literal["NetworkBinding"]
    metadata: Metadata
    spec: NetworkBindingSpec

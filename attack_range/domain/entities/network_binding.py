"""NetworkBinding document: realizes one Network on AWS, Azure, or VMware."""

from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from .common import ApiVersion, Metadata, Name, SpecModel


class AwsNetworkRealize(SpecModel):
    """AWS resource kinds for the network functions."""

    network: Literal["vpc"]
    segment: Literal["subnet"]
    internet: Optional[Literal["internet-gateway"]] = None
    nat: Optional[Literal["nat-gateway"]] = None
    filter: Optional[Literal["security-group"]] = None


class AwsNetworkSettings(SpecModel):
    """AWS placement for the subnets."""

    availability_zone: str = Field(min_length=1)


class AwsNetworkBindingSpec(SpecModel):
    """NetworkBinding body for AWS."""

    network: Name
    provider: Literal["aws"]
    location: str = Field(min_length=1)
    realize: AwsNetworkRealize
    aws: AwsNetworkSettings


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
    realize: VmwareNetworkRealize
    vmware: VmwareNetworkSettings


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

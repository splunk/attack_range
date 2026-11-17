"""Network document: address space, zones, segments, gateways, reachability, perimeter, and filters."""

from ipaddress import IPv4Network
from typing import Annotated, Literal, Optional, Union

from pydantic import AfterValidator, Field, model_validator

from .common import ApiVersion, Metadata, Name, SpecModel, require_unique

Exposure = Literal["internet", "private", "isolated"]
Protocol = Literal["tcp", "udp", "icmp", "any"]


class AddressSpace(SpecModel):
    """The only IPv4 CIDR the network owns."""

    cidr: IPv4Network


class Zone(SpecModel):
    """Trust boundary. Segments in the same zone share an exposure."""

    name: Name
    exposure: Exposure


class Segment(SpecModel):
    """One L3 domain inside a zone, with an explicit CIDR or an allocated prefix length."""

    name: Name
    zone: Name
    cidr: Optional[IPv4Network] = None
    prefix: Optional[int] = Field(None, ge=0, le=32)
    filters: list[Name] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cidr_or_prefix(self) -> "Segment":
        if (self.cidr is None) == (self.prefix is None):
            raise ValueError(f"segment '{self.name}' sets exactly one of cidr or prefix")
        return self


class InternetGateway(SpecModel):
    """Internet gateway on an internet-exposed segment."""

    name: Name
    type: Literal["internet"]
    attach: Name


class NatGateway(SpecModel):
    """NAT gateway on an internet-exposed segment, serving private segments."""

    name: Name
    type: Literal["nat"]
    attach: Name
    serves: list[Name] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_serves(self) -> "NatGateway":
        require_unique(f"served segment on gateway '{self.name}'", self.serves)
        return self


Gateway = Annotated[Union[InternetGateway, NatGateway], Field(discriminator="type")]


class Reachability(SpecModel):
    """Path that leaves the address space."""

    from_: Name = Field(alias="from")
    to: Literal["internet"]
    via: Name


class Perimeter(SpecModel):
    """Outside source prefixes that may enter internet-exposed segments."""

    sources: list[IPv4Network] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_sources(self) -> "Perimeter":
        require_unique("perimeter source", [str(source) for source in self.sources])
        return self


def _check_port_range(value: str) -> str:
    low, _, high = value.partition("-")
    if not (1 <= int(low) <= int(high) <= 65535):
        raise ValueError(f"port range '{value}' needs 1 <= low <= high <= 65535")
    return value


PortRange = Annotated[str, Field(pattern=r"^\d+-\d+$"), AfterValidator(_check_port_range)]
Port = Union[Annotated[int, Field(ge=1, le=65535)], PortRange]


class _Rule(SpecModel):
    protocol: Protocol
    ports: Optional[list[Port]] = Field(None, min_length=1)

    @model_validator(mode="after")
    def _ports_match_protocol(self) -> "_Rule":
        needs_ports = self.protocol in ("tcp", "udp")
        if needs_ports and self.ports is None:
            raise ValueError(f"protocol '{self.protocol}' requires ports")
        if not needs_ports and self.ports is not None:
            raise ValueError(f"protocol '{self.protocol}' does not take ports")
        return self


class IngressRule(_Rule):
    """Allows flows into an interface from the listed sources."""

    direction: Literal["ingress"]
    sources: list[IPv4Network] = Field(min_length=1)


class EgressRule(_Rule):
    """Allows flows out of an interface to the listed destinations."""

    direction: Literal["egress"]
    destinations: list[IPv4Network] = Field(min_length=1)


FilterRule = Annotated[Union[IngressRule, EgressRule], Field(discriminator="direction")]


class Filter(SpecModel):
    """Named allow-list of flows, realized as a security group or equivalent."""

    name: Name
    rules: list[FilterRule] = Field(min_length=1)


class NetworkSpec(SpecModel):
    """Body of a Network document."""

    address_space: AddressSpace
    zones: list[Zone] = Field(min_length=1)
    segments: list[Segment] = Field(min_length=1)
    gateways: list[Gateway] = Field(default_factory=list)
    reachability: list[Reachability] = Field(default_factory=list)
    perimeter: Optional[Perimeter] = None
    filters: list[Filter] = Field(default_factory=list)

    def zone(self, name: str) -> Zone:
        """Return the zone with this name."""
        return next(zone for zone in self.zones if zone.name == name)

    def segment(self, name: str) -> Segment:
        """Return the segment with this name."""
        return next(segment for segment in self.segments if segment.name == name)

    def gateway(self, name: str) -> Union[InternetGateway, NatGateway]:
        """Return the gateway with this name."""
        return next(gateway for gateway in self.gateways if gateway.name == name)

    def exposure(self, segment_name: str) -> Exposure:
        """Return the exposure of the zone that holds this segment."""
        return self.zone(self.segment(segment_name).zone).exposure

    def segment_cidrs(self) -> dict[str, IPv4Network]:
        """Return each segment's CIDR, allocating `prefix` segments in document order."""
        space = self.address_space.cidr
        taken: list[IPv4Network] = []
        cidrs: dict[str, IPv4Network] = {}

        for segment in self.segments:
            if segment.cidr is None:
                continue
            if not segment.cidr.subnet_of(space):
                raise ValueError(f"segment '{segment.name}' cidr {segment.cidr} is outside {space}")
            _claim(segment.name, segment.cidr, taken)
            cidrs[segment.name] = segment.cidr

        for segment in self.segments:
            if segment.prefix is None:
                continue
            if segment.prefix <= space.prefixlen:
                raise ValueError(f"segment '{segment.name}' prefix /{segment.prefix} is not longer than {space}")
            cidr = next(
                (candidate for candidate in space.subnets(new_prefix=segment.prefix)
                 if not any(candidate.overlaps(other) for other in taken)),
                None,
            )
            if cidr is None:
                raise ValueError(f"no free /{segment.prefix} left in {space} for segment '{segment.name}'")
            taken.append(cidr)
            cidrs[segment.name] = cidr

        return {segment.name: cidrs[segment.name] for segment in self.segments}

    @model_validator(mode="after")
    def _references(self) -> "NetworkSpec":
        require_unique("zone", [zone.name for zone in self.zones])
        require_unique("segment", [segment.name for segment in self.segments])
        require_unique("gateway", [gateway.name for gateway in self.gateways])
        require_unique("filter", [filter_.name for filter_ in self.filters])

        zone_names = {zone.name for zone in self.zones}
        segment_names = {segment.name for segment in self.segments}
        filter_names = {filter_.name for filter_ in self.filters}

        for segment in self.segments:
            if segment.zone not in zone_names:
                raise ValueError(f"segment '{segment.name}' names unknown zone '{segment.zone}'")
            for name in segment.filters:
                if name not in filter_names:
                    raise ValueError(f"segment '{segment.name}' names unknown filter '{name}'")

        self.segment_cidrs()
        self._check_gateways(segment_names)
        self._check_reachability(segment_names)
        self._check_perimeter()
        return self

    def _check_gateways(self, segment_names: set[str]) -> None:
        for gateway in self.gateways:
            if gateway.attach not in segment_names:
                raise ValueError(f"gateway '{gateway.name}' attaches to unknown segment '{gateway.attach}'")
            if self.exposure(gateway.attach) != "internet":
                raise ValueError(f"gateway '{gateway.name}' attaches to '{gateway.attach}', which is not internet-exposed")
            if not isinstance(gateway, NatGateway):
                continue
            for name in gateway.serves:
                if name not in segment_names:
                    raise ValueError(f"gateway '{gateway.name}' serves unknown segment '{name}'")
                if self.exposure(name) != "private":
                    raise ValueError(f"gateway '{gateway.name}' serves '{name}', which is not private")
            if not any(isinstance(other, InternetGateway) and other.attach == gateway.attach for other in self.gateways):
                raise ValueError(f"nat gateway '{gateway.name}' needs an internet gateway on segment '{gateway.attach}'")

    def _check_reachability(self, segment_names: set[str]) -> None:
        gateway_names = {gateway.name for gateway in self.gateways}
        seen: set[tuple[str, str]] = set()
        for entry in self.reachability:
            if entry.from_ not in segment_names:
                raise ValueError(f"reachability names unknown segment '{entry.from_}'")
            if entry.via not in gateway_names:
                raise ValueError(f"reachability from '{entry.from_}' names unknown gateway '{entry.via}'")
            if (entry.from_, entry.to) in seen:
                raise ValueError(f"duplicate reachability from '{entry.from_}' to '{entry.to}'")
            seen.add((entry.from_, entry.to))

            exposure = self.exposure(entry.from_)
            gateway = self.gateway(entry.via)
            if exposure == "isolated":
                raise ValueError(f"segment '{entry.from_}' is isolated and cannot reach {entry.to}")
            if exposure == "internet" and not (isinstance(gateway, InternetGateway) and gateway.attach == entry.from_):
                raise ValueError(f"reachability from '{entry.from_}' needs an internet gateway attached to it")
            if exposure == "private" and not (isinstance(gateway, NatGateway) and entry.from_ in gateway.serves):
                raise ValueError(f"reachability from '{entry.from_}' needs a nat gateway that serves it")

    def _check_perimeter(self) -> None:
        if self.perimeter is None:
            return
        space = self.address_space.cidr
        for source in self.perimeter.sources:
            if source.subnet_of(space):
                raise ValueError(f"perimeter source {source} is inside the address space {space}")


def _claim(name: str, cidr: IPv4Network, taken: list[IPv4Network]) -> None:
    for other in taken:
        if cidr.overlaps(other):
            raise ValueError(f"segment '{name}' cidr {cidr} overlaps {other}")
    taken.append(cidr)


class Network(SpecModel):
    """One IPv4 network that NetworkBindings realize and Servers attach to."""

    api_version: ApiVersion
    kind: Literal["Network"]
    metadata: Metadata
    spec: NetworkSpec

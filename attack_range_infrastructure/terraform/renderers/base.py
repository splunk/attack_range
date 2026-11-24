"""Shared pieces of the Terraform renderers: the JSON document builder and naming helpers."""

import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from attack_range.application.cyber_range import CyberRange
from attack_range.application.names import resource_name
from attack_range.domain.entities.network import EgressRule, Filter, IngressRule

FilterRule = IngressRule | EgressRule


class RenderError(ValueError):
    """Raised when a cyber range cannot be expressed on the target provider."""


def cloud_name(cyber_range: CyberRange, name: str, *, limit: Optional[int] = None) -> str:
    """Cloud resource name `<name>-<first uuid group>-<user name>`, e.g. `win-e6fffcb8-ada`.

    `name` is the resource's own name. A provider that allows fewer characters keeps the
    uuid group, shortens `name`, and drops the user name only when the name still does not fit.
    """
    if cyber_range.id is None or not cyber_range.user_name:
        raise RenderError("resource names need the range id and the user name")
    prefix = str(cyber_range.id).split("-", 1)[0]
    try:
        return resource_name(name, prefix, cyber_range.user_name, limit=limit)
    except ValueError as error:
        raise RenderError(str(error)) from error


def tf_name(*parts: str) -> str:
    """Join document names into a Terraform identifier, e.g. ('subnet-1',) -> 'subnet_1'."""
    name = "_".join(re.sub(r"[^A-Za-z0-9_]", "_", part) for part in parts)
    return name if re.match(r"^[A-Za-z_]", name) else f"r_{name}"


def ref(kind: str, name: str, attribute: str) -> str:
    """Interpolation of a resource attribute, e.g. '${aws_subnet.subnet_1.id}'."""
    return f"${{{kind}.{name}.{attribute}}}"


def data_ref(kind: str, name: str, attribute: str) -> str:
    """Interpolation of a data source attribute, e.g. '${data.aws_ami.web.id}'."""
    return f"${{data.{kind}.{name}.{attribute}}}"


def var_ref(name: str) -> str:
    """Interpolation of an input variable."""
    return f"${{var.{name}}}"


def literal(text: str) -> str:
    """Escape a string so Terraform does not treat `${` or `%{` inside it as a template."""
    return text.replace("${", "$${").replace("%{", "%%{")


def port_ranges(rule: FilterRule) -> list[tuple[int, int]]:
    """Return the (from, to) port pairs of a tcp or udp rule; empty for icmp and any."""
    ranges: list[tuple[int, int]] = []
    for port in rule.ports or []:
        if isinstance(port, int):
            ranges.append((port, port))
        else:
            low, _, high = port.partition("-")
            ranges.append((int(low), int(high)))
    return ranges


def rule_prefixes(rule: FilterRule) -> list[str]:
    """Return the sources of an ingress rule or the destinations of an egress rule."""
    networks = rule.sources if isinstance(rule, IngressRule) else rule.destinations
    return [str(network) for network in networks]


class TerraformDocument:
    """Accumulates blocks of one Terraform JSON configuration."""

    def __init__(self) -> None:
        self.required_providers: dict[str, dict[str, str]] = {}
        self.providers: dict[str, dict[str, Any]] = {}
        self.variables: dict[str, dict[str, Any]] = {}
        self.data: dict[str, dict[str, dict[str, Any]]] = {}
        self.resources: dict[str, dict[str, dict[str, Any]]] = {}
        self.outputs: dict[str, dict[str, Any]] = {}

    def require_provider(self, name: str, source: str, version: str, settings: dict[str, Any]) -> None:
        self.required_providers[name] = {"source": source, "version": version}
        self.providers[name] = settings

    def add_variable(self, name: str, body: dict[str, Any]) -> str:
        self.variables[name] = body
        return var_ref(name)

    def add_data(self, kind: str, name: str, body: dict[str, Any]) -> str:
        """Add a data source once and return its name."""
        self.data.setdefault(kind, {}).setdefault(name, body)
        return name

    def add_resource(self, kind: str, name: str, body: dict[str, Any]) -> str:
        """Add a resource and return its name. Names must be unique per kind."""
        blocks = self.resources.setdefault(kind, {})
        if name in blocks:
            raise RenderError(f"duplicate Terraform resource {kind}.{name}")
        blocks[name] = body
        return name

    def has_resource(self, kind: str, name: str) -> bool:
        return name in self.resources.get(kind, {})

    def add_output(self, name: str, value: Any, sensitive: bool = False) -> None:
        self.outputs[name] = {"value": value, **({"sensitive": True} if sensitive else {})}

    def to_dict(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "terraform": {"required_providers": self.required_providers},
            "provider": self.providers,
        }
        for key, value in (
            ("variable", self.variables),
            ("data", self.data),
            ("resource", self.resources),
            ("output", self.outputs),
        ):
            if value:
                document[key] = value
        return document


class Renderer(ABC):
    """Translates a cyber range into the Terraform JSON configuration of one provider."""

    @abstractmethod
    def render(self, cyber_range: CyberRange) -> dict[str, Any]:
        """Return the Terraform JSON document for the cyber range."""

    @staticmethod
    def filter_by_name(cyber_range: CyberRange, name: str) -> Filter:
        return next(filter_ for filter_ in cyber_range.network.spec.filters if filter_.name == name)

    @staticmethod
    def interface_filters(cyber_range: CyberRange, segment: str, filters: list[str]) -> list[str]:
        """Filters of an interface: those of its segment, then its own, without duplicates."""
        names = cyber_range.network.spec.segment(segment).filters + filters
        return list(dict.fromkeys(names))

    @staticmethod
    def internet_gateway_segments(cyber_range: CyberRange) -> list[str]:
        """Segments that have an internet gateway attached."""
        return [gateway.attach for gateway in cyber_range.network.spec.gateways if gateway.type == "internet"]

    @staticmethod
    def nat_routes(cyber_range: CyberRange) -> list[tuple[str, str]]:
        """(segment, nat gateway) pairs from the reachability entries that leave through a NAT."""
        spec = cyber_range.network.spec
        return [
            (entry.from_, entry.via) for entry in spec.reachability if spec.gateway(entry.via).type == "nat"
        ]

    @staticmethod
    def tags(cyber_range: CyberRange, name: str) -> dict[str, str]:
        return {"Name": cloud_name(cyber_range, name, limit=256), "attack-range": cyber_range.name}

    @staticmethod
    def require(value: Optional[object], message: str) -> None:
        if value is None:
            raise RenderError(message)

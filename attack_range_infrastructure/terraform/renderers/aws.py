"""AWS renderer: VPC, subnets, gateways, security groups, network ACL, and EC2 instances."""

from typing import Any

from attack_range.application.cyber_range import CyberRange
from attack_range.domain.entities import Server
from attack_range.domain.entities.network import IngressRule
from attack_range.domain.entities.network_binding import AwsNetworkBindingSpec
from attack_range.domain.entities.server_binding import AwsServerBindingSpec

from .base import (
    RenderError,
    Renderer,
    TerraformDocument,
    data_ref,
    literal,
    port_ranges,
    ref,
    rule_prefixes,
    tf_name,
)

VPC = "vpc"
INTERNET_GATEWAY = "igw"
PERIMETER = "perimeter"
EPHEMERAL_PORTS = (1024, 65535)


class AwsRenderer(Renderer):
    """Renders a cyber range for the hashicorp/aws provider."""

    def render(self, cyber_range: CyberRange) -> dict[str, Any]:
        binding = cyber_range.network_binding.spec
        if not isinstance(binding, AwsNetworkBindingSpec):
            raise RenderError("AwsRenderer needs an aws NetworkBinding")

        doc = TerraformDocument()
        settings: dict[str, Any] = {"region": cyber_range.location}
        if cyber_range.tags:
            settings["default_tags"] = {"tags": cyber_range.tags}
        doc.require_provider("aws", "hashicorp/aws", "~> 5.0", settings)

        self._network(doc, cyber_range, binding)
        self._routing(doc, cyber_range, binding)
        self._filters(doc, cyber_range, binding)
        self._perimeter(doc, cyber_range)

        servers: dict[str, Any] = {}
        for server in cyber_range.servers:
            servers[server.metadata.name] = self._server(doc, cyber_range, server)
        doc.add_output("vpc_id", ref("aws_vpc", VPC, "id"))
        doc.add_output("servers", servers)
        return doc.to_dict()

    def _network(self, doc: TerraformDocument, cyber_range: CyberRange, binding: AwsNetworkBindingSpec) -> None:
        spec = cyber_range.network.spec
        doc.add_resource("aws_vpc", VPC, {
            "cidr_block": str(spec.address_space.cidr),
            "enable_dns_support": True,
            "enable_dns_hostnames": True,
            "tags": self.tags(cyber_range, "vpc"),
        })
        for segment, cidr in spec.segment_cidrs().items():
            doc.add_resource("aws_subnet", tf_name(segment), {
                "vpc_id": ref("aws_vpc", VPC, "id"),
                "cidr_block": str(cidr),
                "availability_zone": binding.aws.availability_zone,
                "map_public_ip_on_launch": False,
                "tags": self.tags(cyber_range, segment),
            })

    def _routing(self, doc: TerraformDocument, cyber_range: CyberRange, binding: AwsNetworkBindingSpec) -> None:
        spec = cyber_range.network.spec
        igw_segments = self.internet_gateway_segments(cyber_range)
        if igw_segments:
            self.require(binding.realize.internet, "network has an internet gateway but realize.internet is not set")
            doc.add_resource("aws_internet_gateway", INTERNET_GATEWAY, {
                "vpc_id": ref("aws_vpc", VPC, "id"),
                "tags": self.tags(cyber_range, "igw"),
            })

        for gateway in spec.gateways:
            if gateway.type != "nat":
                continue
            self.require(binding.realize.nat, f"nat gateway '{gateway.name}' needs realize.nat")
            name = tf_name(gateway.name)
            doc.add_resource("aws_eip", tf_name("nat", gateway.name), {
                "domain": "vpc",
                "tags": self.tags(cyber_range, f"{gateway.name}-eip"),
                "depends_on": [f"aws_internet_gateway.{INTERNET_GATEWAY}"],
            })
            doc.add_resource("aws_nat_gateway", name, {
                "allocation_id": ref("aws_eip", tf_name("nat", gateway.name), "id"),
                "subnet_id": ref("aws_subnet", tf_name(gateway.attach), "id"),
                "tags": self.tags(cyber_range, gateway.name),
                "depends_on": [f"aws_internet_gateway.{INTERNET_GATEWAY}"],
            })

        nat_routes = dict(self.nat_routes(cyber_range))
        for segment in spec.segments:
            table = tf_name(segment.name)
            doc.add_resource("aws_route_table", table, {
                "vpc_id": ref("aws_vpc", VPC, "id"),
                "tags": self.tags(cyber_range, f"{segment.name}-rt"),
            })
            doc.add_resource("aws_route_table_association", table, {
                "subnet_id": ref("aws_subnet", table, "id"),
                "route_table_id": ref("aws_route_table", table, "id"),
            })
            if segment.name in igw_segments:
                doc.add_resource("aws_route", tf_name(segment.name, "internet"), {
                    "route_table_id": ref("aws_route_table", table, "id"),
                    "destination_cidr_block": "0.0.0.0/0",
                    "gateway_id": ref("aws_internet_gateway", INTERNET_GATEWAY, "id"),
                })
            elif segment.name in nat_routes:
                doc.add_resource("aws_route", tf_name(segment.name, "internet"), {
                    "route_table_id": ref("aws_route_table", table, "id"),
                    "destination_cidr_block": "0.0.0.0/0",
                    "nat_gateway_id": ref("aws_nat_gateway", tf_name(nat_routes[segment.name]), "id"),
                })

    def _filters(self, doc: TerraformDocument, cyber_range: CyberRange, binding: AwsNetworkBindingSpec) -> None:
        filters = cyber_range.network.spec.filters
        if filters:
            self.require(binding.realize.filter, "network has filters but realize.filter is not set")
        for filter_ in filters:
            group = tf_name(filter_.name)
            doc.add_resource("aws_security_group", group, {
                "name": f"{cyber_range.name}-{filter_.name}",
                "description": f"Filter {filter_.name} of {cyber_range.name}",
                "vpc_id": ref("aws_vpc", VPC, "id"),
                "tags": self.tags(cyber_range, filter_.name),
            })
            for index, rule in enumerate(filter_.rules):
                ingress = isinstance(rule, IngressRule)
                kind = "aws_vpc_security_group_ingress_rule" if ingress else "aws_vpc_security_group_egress_rule"
                ports = port_ranges(rule) or [None]
                for prefix_index, prefix in enumerate(rule_prefixes(rule)):
                    for port_index, ports_pair in enumerate(ports):
                        body: dict[str, Any] = {
                            "security_group_id": ref("aws_security_group", group, "id"),
                            "cidr_ipv4": prefix,
                            "ip_protocol": "-1" if rule.protocol == "any" else rule.protocol,
                        }
                        if rule.protocol == "icmp":
                            body.update({"from_port": -1, "to_port": -1})
                        elif ports_pair is not None:
                            body.update({"from_port": ports_pair[0], "to_port": ports_pair[1]})
                        doc.add_resource(kind, tf_name(filter_.name, str(index), str(prefix_index), str(port_index)), body)

    def _perimeter(self, doc: TerraformDocument, cyber_range: CyberRange) -> None:
        spec = cyber_range.network.spec
        if spec.perimeter is None:
            return
        exposed = [segment.name for segment in spec.segments if spec.exposure(segment.name) == "internet"]
        if not exposed:
            return

        doc.add_resource("aws_network_acl", PERIMETER, {
            "vpc_id": ref("aws_vpc", VPC, "id"),
            "subnet_ids": [ref("aws_subnet", tf_name(segment), "id") for segment in exposed],
            "tags": self.tags(cyber_range, "perimeter"),
        })
        ingress: list[tuple[str, str, tuple[int, int]]] = [
            (str(source), "-1", (0, 0)) for source in spec.perimeter.sources
        ]
        ingress.append((str(spec.address_space.cidr), "-1", (0, 0)))
        ingress += [("0.0.0.0/0", protocol, EPHEMERAL_PORTS) for protocol in ("tcp", "udp")]
        for index, (cidr, protocol, (low, high)) in enumerate(ingress):
            doc.add_resource("aws_network_acl_rule", tf_name("perimeter_in", str(index)), {
                "network_acl_id": ref("aws_network_acl", PERIMETER, "id"),
                "rule_number": 100 + index * 10,
                "egress": False,
                "protocol": protocol,
                "rule_action": "allow",
                "cidr_block": cidr,
                "from_port": low,
                "to_port": high,
            })
        doc.add_resource("aws_network_acl_rule", "perimeter_out_0", {
            "network_acl_id": ref("aws_network_acl", PERIMETER, "id"),
            "rule_number": 100,
            "egress": True,
            "protocol": "-1",
            "rule_action": "allow",
            "cidr_block": "0.0.0.0/0",
            "from_port": 0,
            "to_port": 0,
        })

    def _server(self, doc: TerraformDocument, cyber_range: CyberRange, server: Server) -> dict[str, Any]:
        binding = cyber_range.binding(server).spec
        if not isinstance(binding, AwsServerBindingSpec):
            raise RenderError(f"server '{server.metadata.name}' needs an aws ServerBinding")
        name = server.metadata.name
        settings = binding.aws
        spec = cyber_range.network.spec
        igw_segments = self.internet_gateway_segments(cyber_range)

        existing_groups: list[str] = []
        for group_name in settings.security_group_names or []:
            data_name = tf_name("sg", group_name)
            doc.add_data("aws_security_group", data_name, {"name": group_name, "vpc_id": ref("aws_vpc", VPC, "id")})
            existing_groups.append(data_ref("aws_security_group", data_name, "id"))

        interfaces: list[dict[str, Any]] = []
        public_ip = None
        for index, interface in enumerate(server.spec.interfaces):
            eni = tf_name(name, interface.name)
            groups = [
                ref("aws_security_group", tf_name(filter_name), "id")
                for filter_name in self.interface_filters(cyber_range, interface.segment, interface.filters)
            ]
            body: dict[str, Any] = {
                "subnet_id": ref("aws_subnet", tf_name(interface.segment), "id"),
                "security_groups": groups + existing_groups,
                "tags": self.tags(cyber_range, f"{name}-{interface.name}"),
            }
            if interface.address != "auto":
                body["private_ips"] = [str(interface.address)]
            doc.add_resource("aws_network_interface", eni, body)
            interfaces.append({"network_interface_id": ref("aws_network_interface", eni, "id"), "device_index": index})

            if interface.public:
                self.require(binding.realize.public, f"server '{name}' has a public interface but realize.public is not set")
                if spec.exposure(interface.segment) != "internet" or interface.segment not in igw_segments:
                    raise RenderError(
                        f"server '{name}' interface '{interface.name}' is public but segment "
                        f"'{interface.segment}' has no internet gateway"
                    )
                doc.add_resource("aws_eip", eni, {
                    "domain": "vpc",
                    "network_interface": ref("aws_network_interface", eni, "id"),
                    "tags": self.tags(cyber_range, f"{name}-{interface.name}-eip"),
                    "depends_on": [f"aws_internet_gateway.{INTERNET_GATEWAY}"],
                })
                if public_ip is None:
                    public_ip = ref("aws_eip", eni, "public_ip")

        instance: dict[str, Any] = {
            "ami": settings.ami,
            "instance_type": settings.instance_type,
            "key_name": settings.key_name,
            "network_interface": interfaces,
            "root_block_device": {
                "volume_size": settings.root_volume.size_gib,
                "volume_type": settings.root_volume.type,
            },
            "tags": self.tags(cyber_range, name),
        }
        if settings.iam_instance_profile:
            instance["iam_instance_profile"] = settings.iam_instance_profile
        user_data = cyber_range.user_data(server)
        if user_data is not None:
            instance["user_data"] = literal(user_data)
        doc.add_resource("aws_instance", tf_name(name), instance)

        return {"private_ip": ref("aws_instance", tf_name(name), "private_ip"), "public_ip": public_ip}

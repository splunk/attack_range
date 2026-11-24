"""Azure renderer: resource group, virtual network, NSGs, NAT gateways, and virtual machines.

Azure allows one NSG per subnet and one per NIC, and traffic must pass both. The subnet NSG
holds the perimeter (internet zones) or the internet block (isolated zones); the NIC NSG holds
the merged filters of the interface and its segment, like the security groups of an AWS ENI.
"""

import base64
import json
from typing import Any, Optional

from attack_range.application.cyber_range import CyberRange
from attack_range.domain.entities import Server
from attack_range.domain.entities.network import IngressRule
from attack_range.domain.entities.network_binding import AzureNetworkBindingSpec
from attack_range.domain.entities.server import Interface
from attack_range.domain.entities.server_binding import AzureServerBindingSpec, AzureServerSettings

from ..wireguard import WireGuardError, access_sources, listen_port, load_gateway, overlay_network

from .base import (
    RenderError,
    Renderer,
    TerraformDocument,
    cloud_name,
    data_ref,
    literal,
    port_ranges,
    ref,
    rule_prefixes,
    tf_name,
)

RESOURCE_GROUP = "network"
VIRTUAL_NETWORK = "network"
VPN = "wireguard"
FIRST_PRIORITY = 100
LAST_PRIORITY = 4096
PROTOCOLS = {"tcp": "Tcp", "udp": "Udp", "icmp": "Icmp", "any": "*"}


class AzureRenderer(Renderer):
    """Renders a cyber range for the hashicorp/azurerm provider."""

    def render(self, cyber_range: CyberRange) -> dict[str, Any]:
        binding = cyber_range.network_binding.spec
        if not isinstance(binding, AzureNetworkBindingSpec):
            raise RenderError("AzureRenderer needs an azure NetworkBinding")

        doc = TerraformDocument()
        doc.require_provider("azurerm", "hashicorp/azurerm", "~> 4.0", {"features": {}})

        self._network(doc, cyber_range, binding)
        self._subnet_security(doc, cyber_range)
        self._nat_gateways(doc, cyber_range, binding)

        servers: dict[str, Any] = {}
        for server in cyber_range.servers:
            servers[server.metadata.name] = self._server(doc, cyber_range, binding, server)
        self._wireguard(doc, cyber_range)
        doc.add_output("resource_group", ref("azurerm_resource_group", RESOURCE_GROUP, "name"))
        doc.add_output("virtual_network_id", ref("azurerm_virtual_network", VIRTUAL_NETWORK, "id"))
        doc.add_output("servers", servers)
        return doc.to_dict()

    def _network(self, doc: TerraformDocument, cyber_range: CyberRange, binding: AzureNetworkBindingSpec) -> None:
        spec = cyber_range.network.spec
        tags = self._tags(cyber_range)
        doc.add_resource("azurerm_resource_group", RESOURCE_GROUP, {
            "name": cloud_name(cyber_range, binding.azure.resource_group, limit=90),
            "location": cyber_range.location,
            "tags": tags,
        })
        doc.add_resource("azurerm_virtual_network", VIRTUAL_NETWORK, {
            "name": cloud_name(cyber_range, cyber_range.name, limit=64),
            "location": cyber_range.location,
            "resource_group_name": self._group_name(),
            "address_space": [str(spec.address_space.cidr)],
            "tags": tags,
        })
        for segment, cidr in spec.segment_cidrs().items():
            doc.add_resource("azurerm_subnet", tf_name(segment), {
                "name": cloud_name(cyber_range, segment, limit=80),
                "resource_group_name": self._group_name(),
                "virtual_network_name": ref("azurerm_virtual_network", VIRTUAL_NETWORK, "name"),
                "address_prefixes": [str(cidr)],
                "default_outbound_access_enabled": spec.exposure(segment) == "internet",
            })

    def _subnet_security(self, doc: TerraformDocument, cyber_range: CyberRange) -> None:
        spec = cyber_range.network.spec
        for segment in spec.segments:
            exposure = spec.exposure(segment.name)
            rules: list[dict[str, Any]] = []
            if exposure == "internet" and spec.perimeter is not None:
                rules.append({
                    "name": "AllowPerimeterInbound",
                    "direction": "Inbound",
                    "access": "Allow",
                    "protocol": "*",
                    "source_address_prefixes": [str(source) for source in spec.perimeter.sources],
                    "destination_address_prefix": "*",
                    "destination_port_range": "*",
                })
            elif exposure == "isolated":
                rules.append({
                    "name": "DenyInternetOutbound",
                    "direction": "Outbound",
                    "access": "Deny",
                    "protocol": "*",
                    "source_address_prefix": "*",
                    "destination_address_prefix": "Internet",
                    "destination_port_range": "*",
                })
            if not rules:
                continue
            group = tf_name("subnet", segment.name)
            self._security_group(doc, cyber_range, group, segment.name, rules)
            doc.add_resource("azurerm_subnet_network_security_group_association", group, {
                "subnet_id": ref("azurerm_subnet", tf_name(segment.name), "id"),
                "network_security_group_id": ref("azurerm_network_security_group", group, "id"),
            })

    def _nat_gateways(self, doc: TerraformDocument, cyber_range: CyberRange, binding: AzureNetworkBindingSpec) -> None:
        spec = cyber_range.network.spec
        for gateway in spec.gateways:
            if gateway.type != "nat":
                continue
            self.require(binding.realize.nat, f"nat gateway '{gateway.name}' needs realize.nat")
            name = tf_name(gateway.name)
            doc.add_resource("azurerm_public_ip", tf_name("nat", gateway.name), {
                "name": cloud_name(cyber_range, gateway.name, limit=80),
                "location": cyber_range.location,
                "resource_group_name": self._group_name(),
                "allocation_method": "Static",
                "sku": "Standard",
                "tags": self._tags(cyber_range),
            })
            doc.add_resource("azurerm_nat_gateway", name, {
                "name": cloud_name(cyber_range, gateway.name, limit=80),
                "location": cyber_range.location,
                "resource_group_name": self._group_name(),
                "sku_name": "Standard",
                "tags": self._tags(cyber_range),
            })
            doc.add_resource("azurerm_nat_gateway_public_ip_association", name, {
                "nat_gateway_id": ref("azurerm_nat_gateway", name, "id"),
                "public_ip_address_id": ref("azurerm_public_ip", tf_name("nat", gateway.name), "id"),
            })
        for segment, gateway_name in self.nat_routes(cyber_range):
            doc.add_resource("azurerm_subnet_nat_gateway_association", tf_name(segment), {
                "subnet_id": ref("azurerm_subnet", tf_name(segment), "id"),
                "nat_gateway_id": ref("azurerm_nat_gateway", tf_name(gateway_name), "id"),
            })

    def _filter_rules(self, cyber_range: CyberRange, filter_names: list[str]) -> list[dict[str, Any]]:
        """NSG rules for an allow-list of filters, closed by deny-all rules in both directions."""
        rules: list[dict[str, Any]] = []
        for filter_name in filter_names:
            for index, rule in enumerate(self.filter_by_name(cyber_range, filter_name).rules):
                ingress = isinstance(rule, IngressRule)
                body: dict[str, Any] = {
                    "name": f"{filter_name}-{index}",
                    "direction": "Inbound" if ingress else "Outbound",
                    "access": "Allow",
                    "protocol": PROTOCOLS[rule.protocol],
                    "source_port_range": "*",
                }
                prefixes = rule_prefixes(rule)
                if ingress:
                    body.update({"source_address_prefixes": prefixes, "destination_address_prefix": "*"})
                else:
                    body.update({"source_address_prefix": "*", "destination_address_prefixes": prefixes})
                ports = port_ranges(rule)
                if ports:
                    body["destination_port_ranges"] = [str(low) if low == high else f"{low}-{high}" for low, high in ports]
                else:
                    body["destination_port_range"] = "*"
                rules.append(body)
        for direction in ("Inbound", "Outbound"):
            rules.append({
                "name": f"DenyAll{direction}",
                "direction": direction,
                "access": "Deny",
                "protocol": "*",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "destination_port_range": "*",
                "priority": LAST_PRIORITY,
            })
        return rules

    def _security_group(
        self, doc: TerraformDocument, cyber_range: CyberRange, group: str, name: str, rules: list[dict[str, Any]]
    ) -> None:
        doc.add_resource("azurerm_network_security_group", group, {
            "name": cloud_name(cyber_range, name, limit=80),
            "location": cyber_range.location,
            "resource_group_name": self._group_name(),
            "tags": self._tags(cyber_range),
        })
        next_priority = {"Inbound": FIRST_PRIORITY, "Outbound": FIRST_PRIORITY}
        for rule in rules:
            body = {"source_port_range": "*", **rule}
            if "priority" not in body:
                body["priority"] = next_priority[body["direction"]]
                next_priority[body["direction"]] += 10
                if body["priority"] >= LAST_PRIORITY:
                    raise RenderError(f"network security group '{name}' has too many rules")
            body.update({
                "resource_group_name": self._group_name(),
                "network_security_group_name": ref("azurerm_network_security_group", group, "name"),
            })
            doc.add_resource("azurerm_network_security_rule", tf_name(group, rule["name"]), body)

    def _server(
        self, doc: TerraformDocument, cyber_range: CyberRange, network: AzureNetworkBindingSpec, server: Server
    ) -> dict[str, Any]:
        binding = cyber_range.binding(server).spec
        if not isinstance(binding, AzureServerBindingSpec):
            raise RenderError(f"server '{server.metadata.name}' needs an azure ServerBinding")
        name = server.metadata.name
        settings = binding.azure
        group_name = settings.resource_group or self._group_name()

        nic_ids: list[str] = []
        public_ip: Optional[str] = None
        for interface in server.spec.interfaces:
            nic = tf_name(name, interface.name)
            ip_configuration: dict[str, Any] = {
                "name": "primary",
                "subnet_id": ref("azurerm_subnet", tf_name(interface.segment), "id"),
                "private_ip_address_allocation": "Dynamic" if interface.address == "auto" else "Static",
            }
            if interface.address != "auto":
                ip_configuration["private_ip_address"] = str(interface.address)
            if interface.public:
                self.require(binding.realize.public, f"server '{name}' has a public interface but realize.public is not set")
                doc.add_resource("azurerm_public_ip", nic, {
                    "name": cloud_name(cyber_range, f"{name}-{interface.name}", limit=80),
                    "location": cyber_range.location,
                    "resource_group_name": group_name,
                    "allocation_method": "Static",
                    "sku": "Standard",
                    "tags": self._tags(cyber_range),
                })
                ip_configuration["public_ip_address_id"] = ref("azurerm_public_ip", nic, "id")
                if public_ip is None:
                    public_ip = ref("azurerm_public_ip", nic, "ip_address")
            doc.add_resource("azurerm_network_interface", nic, {
                "name": cloud_name(cyber_range, f"{name}-{interface.name}", limit=80),
                "location": cyber_range.location,
                "resource_group_name": group_name,
                "ip_configuration": [ip_configuration],
                "tags": self._tags(cyber_range),
            })
            nic_ids.append(ref("azurerm_network_interface", nic, "id"))
            self._interface_security(
                doc, cyber_range, network, settings.network_security_group, nic, f"{name}-{interface.name}", interface
            )

        password = server.spec.access.password
        windows = bool(settings.admin_password_secret) or password is not None
        vm: dict[str, Any] = {
            "name": cloud_name(cyber_range, name, limit=15 if windows else 64),
            "location": cyber_range.location,
            "resource_group_name": group_name,
            "size": settings.size,
            "admin_username": server.spec.access.username,
            "network_interface_ids": nic_ids,
            "os_disk": {
                "caching": "ReadWrite",
                "storage_account_type": settings.os_disk.storage_account_type,
                "disk_size_gb": settings.os_disk.size_gib,
            },
            "tags": self._tags(cyber_range),
        }
        vm.update(self._source_image(doc, name, settings, cyber_range.location))
        if settings.zone:
            vm["zone"] = settings.zone
        user_data = cyber_range.user_data(server)
        if user_data is not None:
            vm["custom_data"] = base64.b64encode(user_data.encode()).decode()

        if windows:
            kind = "azurerm_windows_virtual_machine"
            vm["computer_name"] = cloud_name(cyber_range, name, limit=15)
            if settings.admin_password_secret:
                vm["admin_password"] = doc.add_variable(
                    tf_name(settings.admin_password_secret),
                    {"type": "string", "sensitive": True, "description": f"Admin password of server {name}"},
                )
            else:
                vm["admin_password"] = literal(password or "")
        else:
            kind = "azurerm_linux_virtual_machine"
            vm["disable_password_authentication"] = True
            keys = list(server.spec.access.authorized_keys)
            if server.spec.access.ssh_key == "range" and cyber_range.ssh_public_key:
                if cyber_range.ssh_public_key not in keys:
                    keys.append(cyber_range.ssh_public_key)
            vm["admin_ssh_key"] = [
                {"username": server.spec.access.username, "public_key": key} for key in keys
            ]
        doc.add_resource(kind, tf_name(name), vm)
        if windows and user_data is not None:
            self._windows_bootstrap(doc, name, user_data)

        return {"private_ip": ref(kind, tf_name(name), "private_ip_address"), "public_ip": public_ip}

    @staticmethod
    def _source_image(
        doc: TerraformDocument, name: str, settings: AzureServerSettings, location: str
    ) -> dict[str, Any]:
        """Marketplace reference, or a looked-up version, or a custom image id."""
        if settings.image is not None:
            image = settings.image
            return {"source_image_reference": {
                "publisher": image.publisher,
                "offer": image.offer,
                "sku": image.sku,
                "version": image.version,
            }}
        if settings.image_publisher is not None and settings.image_offer is not None and settings.image_sku is not None:
            data_name = doc.add_data("azurerm_platform_image", tf_name(name), {
                "location": location,
                "publisher": settings.image_publisher,
                "offer": settings.image_offer,
                "sku": settings.image_sku,
            })
            return {"source_image_reference": {
                "publisher": settings.image_publisher,
                "offer": settings.image_offer,
                "sku": settings.image_sku,
                "version": data_ref("azurerm_platform_image", data_name, "version"),
            }}
        return {"source_image_id": settings.image_id}

    @staticmethod
    def _windows_bootstrap(doc: TerraformDocument, name: str, script: str) -> None:
        """Run the bootstrap script. Azure does not execute Windows custom data."""
        text = script.strip()
        if text.startswith("<powershell>"):
            text = text[len("<powershell>"):].strip()
        if text.endswith("</powershell>"):
            text = text[: -len("</powershell>")].strip()
        encoded = base64.b64encode(text.encode("utf-16le")).decode()
        doc.add_resource("azurerm_virtual_machine_extension", tf_name(name, "bootstrap"), {
            "name": "bootstrap",
            "virtual_machine_id": ref("azurerm_windows_virtual_machine", tf_name(name), "id"),
            "publisher": "Microsoft.Compute",
            "type": "CustomScriptExtension",
            "type_handler_version": "1.10",
            "protected_settings": json.dumps({
                "commandToExecute": f"powershell -ExecutionPolicy Bypass -EncodedCommand {encoded}",
            }),
        })

    def _wireguard(self, doc: TerraformDocument, cyber_range: CyberRange) -> None:
        """Ubuntu gateway from config/wireguard, placed on the range's internet subnet."""
        segments = self.internet_gateway_segments(cyber_range)
        if not segments:
            raise RenderError("a wireguard gateway needs an internet gateway on an internet-exposed segment")
        segment = segments[0]
        try:
            server, binding = load_gateway("azure")
            port = listen_port(server)
            overlay_network(cyber_range.network.spec.address_space.cidr)
        except WireGuardError as error:
            raise RenderError(str(error)) from error
        if not isinstance(binding.spec, AzureServerBindingSpec):
            raise RenderError("wireguard Azure binding is not an azure ServerBinding")
        settings = binding.spec.azure
        name = server.metadata.name
        sources = access_sources(
            None if cyber_range.network.spec.perimeter is None else list(cyber_range.network.spec.perimeter.sources)
        )
        doc.add_resource("azurerm_public_ip", VPN, {
            "name": cloud_name(cyber_range, name, limit=80),
            "location": cyber_range.location,
            "resource_group_name": self._group_name(),
            "allocation_method": "Static",
            "sku": "Standard",
            "tags": self._tags(cyber_range),
        })
        doc.add_resource("azurerm_network_interface", VPN, {
            "name": cloud_name(cyber_range, name, limit=80),
            "location": cyber_range.location,
            "resource_group_name": self._group_name(),
            "ip_forwarding_enabled": True,
            "ip_configuration": [{
                "name": "primary",
                "subnet_id": ref("azurerm_subnet", tf_name(segment), "id"),
                "private_ip_address_allocation": "Dynamic",
                "public_ip_address_id": ref("azurerm_public_ip", VPN, "id"),
            }],
            "tags": self._tags(cyber_range),
        })
        self._security_group(doc, cyber_range, VPN, name, [
            {
                "name": "AllowWireGuard",
                "direction": "Inbound",
                "access": "Allow",
                "protocol": "Udp",
                "source_address_prefixes": sources,
                "destination_address_prefix": "*",
                "destination_port_range": str(port),
            },
            {
                "name": "AllowSsh",
                "direction": "Inbound",
                "access": "Allow",
                "protocol": "Tcp",
                "source_address_prefixes": sources,
                "destination_address_prefix": "*",
                "destination_port_range": "22",
            },
            {
                "name": "AllowAllOutbound",
                "direction": "Outbound",
                "access": "Allow",
                "protocol": "*",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "destination_port_range": "*",
            },
        ])
        doc.add_resource("azurerm_network_interface_security_group_association", VPN, {
            "network_interface_id": ref("azurerm_network_interface", VPN, "id"),
            "network_security_group_id": ref("azurerm_network_security_group", VPN, "id"),
        })
        vm: dict[str, Any] = {
            "name": cloud_name(cyber_range, name, limit=64),
            "location": cyber_range.location,
            "resource_group_name": self._group_name(),
            "size": settings.size,
            "admin_username": server.spec.access.username,
            "network_interface_ids": [ref("azurerm_network_interface", VPN, "id")],
            "os_disk": {
                "caching": "ReadWrite",
                "storage_account_type": settings.os_disk.storage_account_type,
                "disk_size_gb": settings.os_disk.size_gib,
            },
            "disable_password_authentication": True,
            "tags": self._tags(cyber_range),
        }
        if settings.image is None:
            raise RenderError("wireguard Azure binding needs an image")
        vm["source_image_reference"] = {
            "publisher": settings.image.publisher,
            "offer": settings.image.offer,
            "sku": settings.image.sku,
            "version": settings.image.version,
        }
        if cyber_range.ssh_public_key:
            vm["admin_ssh_key"] = [{"username": server.spec.access.username, "public_key": cyber_range.ssh_public_key}]
        doc.add_resource("azurerm_linux_virtual_machine", VPN, vm)
        doc.add_output("wireguard", {
            "public_ip": ref("azurerm_public_ip", VPN, "ip_address"),
            "private_ip": ref("azurerm_network_interface", VPN, "private_ip_address"),
        })

    def _interface_security(
        self,
        doc: TerraformDocument,
        cyber_range: CyberRange,
        network: AzureNetworkBindingSpec,
        existing_group: Optional[str],
        nic: str,
        nic_name: str,
        interface: Interface,
    ) -> None:
        filter_names = self.interface_filters(cyber_range, interface.segment, interface.filters)
        if filter_names and existing_group:
            raise RenderError(f"interface '{nic}' has filters and an existing networkSecurityGroup; set only one")
        if filter_names:
            self.require(network.realize.filter, "network has filters but realize.filter is not set")
            group = tf_name("nic", nic)
            self._security_group(doc, cyber_range, group, nic_name, self._filter_rules(cyber_range, filter_names))
            group_id = ref("azurerm_network_security_group", group, "id")
        elif existing_group:
            data_name = doc.add_data("azurerm_network_security_group", tf_name(existing_group), {
                "name": existing_group,
                "resource_group_name": self._group_name(),
            })
            group_id = data_ref("azurerm_network_security_group", data_name, "id")
        else:
            return
        doc.add_resource("azurerm_network_interface_security_group_association", nic, {
            "network_interface_id": ref("azurerm_network_interface", nic, "id"),
            "network_security_group_id": group_id,
        })

    @staticmethod
    def _tags(cyber_range: CyberRange) -> dict[str, str]:
        """Azure has no provider-wide default tags, so every taggable resource gets them."""
        return {**cyber_range.tags, "attack-range": cyber_range.name}

    @staticmethod
    def _group_name() -> str:
        return ref("azurerm_resource_group", RESOURCE_GROUP, "name")

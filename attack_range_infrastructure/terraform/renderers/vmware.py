"""VMware renderer: looks up existing vSphere objects and clones one virtual machine per server.

The v0.1 VMware binding maps segments onto existing port groups, so gateways, filters, and the
perimeter are realized by the existing environment and produce no Terraform objects.
"""

import base64
from typing import Any, Optional

from attack_range.application.cyber_range import CyberRange
from attack_range.domain.entities import Server
from attack_range.domain.entities.network_binding import VmwareNetworkBindingSpec
from attack_range.domain.entities.server_binding import VmwareServerBindingSpec

from .base import RenderError, Renderer, TerraformDocument, cloud_name, data_ref, ref, tf_name

DATACENTER = "network"


class VmwareRenderer(Renderer):
    """Renders a cyber range for the hashicorp/vsphere provider."""

    def render(self, cyber_range: CyberRange) -> dict[str, Any]:
        binding = cyber_range.network_binding.spec
        if not isinstance(binding, VmwareNetworkBindingSpec):
            raise RenderError("VmwareRenderer needs a vmware NetworkBinding")

        doc = TerraformDocument()
        doc.require_provider("vsphere", "hashicorp/vsphere", "~> 2.0", {})

        doc.add_data("vsphere_datacenter", DATACENTER, {"name": binding.vmware.datacenter})
        used_segments = {interface.segment for server in cyber_range.servers for interface in server.spec.interfaces}
        for segment in sorted(used_segments):
            port_group = binding.vmware.segments.get(segment)
            if port_group is None:
                raise RenderError(f"segment '{segment}' has no port group in the vmware NetworkBinding")
            doc.add_data("vsphere_network", tf_name(segment), {
                "name": port_group.port_group,
                "datacenter_id": data_ref("vsphere_datacenter", DATACENTER, "id"),
            })

        servers: dict[str, Any] = {}
        for server in cyber_range.servers:
            servers[server.metadata.name] = self._server(doc, cyber_range, binding, server)
        doc.add_output("servers", servers)
        return doc.to_dict()

    def _server(
        self, doc: TerraformDocument, cyber_range: CyberRange, network: VmwareNetworkBindingSpec, server: Server
    ) -> dict[str, Any]:
        binding = cyber_range.binding(server).spec
        if not isinstance(binding, VmwareServerBindingSpec):
            raise RenderError(f"server '{server.metadata.name}' needs a vmware ServerBinding")
        name = server.metadata.name
        key = tf_name(name)
        settings = binding.vmware
        cidrs = cyber_range.network.spec.segment_cidrs()

        datacenter_id = data_ref("vsphere_datacenter", DATACENTER, "id")
        if settings.datacenter and settings.datacenter != network.vmware.datacenter:
            doc.add_data("vsphere_datacenter", key, {"name": settings.datacenter})
            datacenter_id = data_ref("vsphere_datacenter", key, "id")

        doc.add_data("vsphere_datastore", key, {"name": settings.datastore, "datacenter_id": datacenter_id})
        if settings.cluster:
            doc.add_data("vsphere_compute_cluster", key, {"name": settings.cluster, "datacenter_id": datacenter_id})
            resource_pool_id = data_ref("vsphere_compute_cluster", key, "resource_pool_id")
        else:
            doc.add_data("vsphere_host", key, {"name": settings.host, "datacenter_id": datacenter_id})
            resource_pool_id = data_ref("vsphere_host", key, "resource_pool_id")
        doc.add_data("vsphere_virtual_machine", tf_name(name, "template"), {
            "name": settings.template,
            "datacenter_id": datacenter_id,
        })

        def template(attribute: str) -> str:
            return data_ref("vsphere_virtual_machine", tf_name(name, "template"), attribute)

        network_interfaces: list[dict[str, Any]] = []
        customize_interfaces: list[dict[str, Any]] = []
        for interface in server.spec.interfaces:
            if interface.public:
                raise RenderError(f"server '{name}' interface '{interface.name}' is public, which vmware cannot realize")
            network_interfaces.append({
                "network_id": data_ref("vsphere_network", tf_name(interface.segment), "id"),
                "adapter_type": template("network_interface_types[0]"),
            })
            if interface.address == "auto":
                customize_interfaces.append({})
            else:
                customize_interfaces.append({
                    "ipv4_address": str(interface.address),
                    "ipv4_netmask": cidrs[interface.segment].prefixlen,
                })

        customize: dict[str, Any] = {
            "linux_options": {"host_name": cloud_name(cyber_range, name, limit=63), "domain": "local"},
            "network_interface": customize_interfaces,
        }
        primary = server.spec.primary_interface
        if primary.address != "auto":
            customize["ipv4_gateway"] = str(next(cidrs[primary.segment].hosts()))
        if settings.dns:
            customize["dns_server_list"] = [str(address) for address in settings.dns]

        disk_size: Any = template("disks[0].size")
        if settings.disk and settings.disk.size_gib:
            disk_size = settings.disk.size_gib

        vm: dict[str, Any] = {
            "name": cloud_name(cyber_range, name, limit=80),
            "resource_pool_id": resource_pool_id,
            "datastore_id": data_ref("vsphere_datastore", key, "id"),
            "num_cpus": settings.cpu or template("num_cpus"),
            "memory": settings.memory_mib or template("memory"),
            "guest_id": template("guest_id"),
            "firmware": template("firmware"),
            "scsi_type": template("scsi_type"),
            "network_interface": network_interfaces,
            "disk": [{
                "label": "disk0",
                "size": disk_size,
                "thin_provisioned": template("disks[0].thin_provisioned"),
            }],
            "clone": {"template_uuid": template("id"), "customize": customize},
        }
        if settings.folder:
            vm["folder"] = settings.folder
        extra_config = self._extra_config(cyber_range, server)
        if extra_config:
            vm["extra_config"] = extra_config
        doc.add_resource("vsphere_virtual_machine", key, vm)

        return {"private_ip": ref("vsphere_virtual_machine", key, "default_ip_address"), "public_ip": None}

    @staticmethod
    def _extra_config(cyber_range: CyberRange, server: Server) -> Optional[dict[str, str]]:
        user_data = cyber_range.user_data(server)
        if user_data is None:
            return None
        return {
            "guestinfo.userdata": base64.b64encode(user_data.encode()).decode(),
            "guestinfo.userdata.encoding": "base64",
        }

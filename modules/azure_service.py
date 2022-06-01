import sys
import os
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import AzureCliCredential
from azure.mgmt.network import NetworkManagementClient



def get_all_instances(key_name):
    credential = AzureCliCredential()
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    compute_client = ComputeManagementClient(credential, subscription_id)

    instances = []

    for vm in compute_client.virtual_machines.list("ar-rg-" + key_name):
        vm_extended = compute_client.virtual_machines.get("ar-rg-" + key_name, vm.name, expand='instanceView')
        if vm_extended.instance_view.statuses[1].display_status not in ["VM deallocating", "VM deallocated"]:
            vm_obj = {}
            if vm_extended.instance_view.statuses[1].display_status == "VM running":
                vm_obj['public_ip'] = get_public_ip(vm_extended)
            vm_obj['vm_obj'] = vm_extended
            instances.append(vm_obj)

    return instances


def get_instance(instance_name, key_name):
    instances = get_all_instances(key_name)

    for instance in instances:
        if instance['vm_obj'].name == instance_name:
            return instance


def get_public_ip(vm_obj):
    credential = AzureCliCredential()
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    network_client = NetworkManagementClient(credential ,subscription_id)
    interface = vm_obj.network_profile.network_interfaces[0]
    name=" ".join(interface.id.split('/')[-1:])
    sub="".join(interface.id.split('/')[4])
    ip_config=network_client.network_interfaces.get(sub, name).ip_configurations
    ip_reference = ip_config[0].public_ip_address
    ip_reference = ip_reference.id.split('/')
    ip_group = ip_reference[4]
    ip_name = ip_reference[8]
    public_ip = network_client.public_ip_addresses.get(ip_group, ip_name)
    return public_ip.ip_address
# NetworkBinding

A NetworkBinding realizes one [Network](network.md) on one provider. The network document stays free of provider resource names. A provider that cannot realize a function rejects the binding. The network document remains valid.

A [ServerBinding](server-binding.md) is a separate kind. It places a server into the subnet, or port group, that this binding emits for a segment.

## Envelope

| Field | Required | Meaning |
|---|---|---|
| `apiVersion` | yes | `v0.1` |
| `kind` | yes | `NetworkBinding` |
| `metadata.name` | yes | Name of this binding. |

`metadata.name` matches `[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?`.

## Spec

| Field | Required | Meaning |
|---|---|---|
| `network` | yes | `metadata.name` of the network to realize. |
| `provider` | yes | `aws`, `azure`, or `vmware`. |
| `location` | yes | Provider location. The provider defines the legal values. |
| `realize` | yes | Map from language functions to the provider resource kind that implements them. |
| `azure` | when `provider` is `azure` | Azure resource group. |
| `vmware` | when `provider` is `vmware` | Datacenter and the port group for each segment. |

Azure and VMware require the block that matches `provider`. The other provider blocks are absent. AWS has no provider block.

## `realize` keys

| Key | Realizes |
|---|---|
| `network` | The network and its address space. |
| `segment` | Each segment. |
| `internet` | Each gateway of type `internet`. |
| `nat` | Each gateway of type `nat`. |
| `filter` | Each filter. Required when the network defines one or more filters. |

A key may emit zero, one, or several provider resources. A key the compiler does not know is invalid. A key whose value is `existing` records that the function is already present and emits nothing.

## AWS

`location` is a region, for example `eu-central-1`.

| Key | Value | Emission |
|---|---|---|
| `network` | `vpc` | One VPC with the address space CIDR. |
| `segment` | `subnet` | One subnet per segment. |
| `internet` | `internet-gateway` | One internet gateway, plus a default route on the attach segment. |
| `nat` | `nat-gateway` | One NAT gateway in the attach segment, plus a default route on each served segment that reachability selects. |
| `filter` | `security-group` | One security group per filter. The compiler attaches that group to every interface that lists the filter, and to every interface whose segment lists the filter. |

Every subnet is placed in the first availability zone of `location`, formed by appending `a`. A region of `eu-central-1` places the subnets in `eu-central-1a`. There is no availability zone field to set.

A segment filter is the same security group on each interface in the segment. The compiler does not create a network ACL. Several groups on one interface allow the union of their rules. The perimeter is applied to ingress sources on `internet` segments before those rules are written.

## Azure

`location` is a region, for example `westeurope`.

| Key | Value | Emission |
|---|---|---|
| `network` | `virtual-network` | One virtual network with the address space CIDR. |
| `segment` | `subnet` | One subnet per segment. |
| `nat` | `nat-gateway` | One NAT gateway associated with each served subnet that reachability selects. |
| `filter` | `network-security-group` | One network security group per interface that has an effective filter set. |

Azure has no standalone internet-gateway resource. Omit the `internet` key. A public address is allocated later by a ServerBinding for an interface that sets `public: true`.

| Field | Required | Meaning |
|---|---|---|
| `azure.resourceGroup` | yes | Resource group that contains the virtual network. A ServerBinding in the same location uses this group when it omits its own. |

Azure associates one network security group with a NIC, and a subnet group is combined with the NIC group by intersection. The compiler merges the segment filters and the interface filters into the NIC group so the effective set allows the union of those rules. It does not attach a second group to the subnet. The perimeter is applied to ingress sources on `internet` segments before those rules are written.

## VMware

`location` is the site or vCenter name, for example `site-1`. v0.1 maps the network onto port groups that already exist.

| Key | Value | Emission |
|---|---|---|
| `network` | `existing` | No network object is created. |
| `segment` | `port-group` | Each segment is identified with an existing port group. |
| `internet` | `existing` | The upstream gateway of the edge port group. |
| `nat` | `existing` | The upstream gateway already provides egress for the private port group. |
| `filter` | `existing` | No firewall is emitted. The port group already enforces the filters, and the upstream gateway already admits the perimeter sources. |

| Field | Required | Meaning |
|---|---|---|
| `vmware.datacenter` | yes | Datacenter that holds the port groups. |
| `vmware.segments.<name>.portGroup` | yes | Existing port group for that segment. Every segment in the network has an entry. |

## Examples

- [tmp/lab.network-binding.aws.yaml](../tmp/lab.network-binding.aws.yaml) for AWS
- [tmp/lab.network-binding.azure.yaml](../tmp/lab.network-binding.azure.yaml) for Azure
- [tmp/lab.network-binding.vmware.yaml](../tmp/lab.network-binding.vmware.yaml) for VMware

These three files are alternative realizations of the same network.

# ServerBinding

A ServerBinding realizes one [Server](server.md) on one provider. It is a separate kind from [NetworkBinding](network-binding.md). The server document stays free of instance types, image ids, disk types, and placement.

`provider` and `location` match the NetworkBinding that realizes `server.spec.network`. The compiler places each interface in the subnet or port group that the NetworkBinding emitted for that segment.

## Envelope

| Field | Required | Meaning |
|---|---|---|
| `apiVersion` | yes | `v0.1` |
| `kind` | yes | `ServerBinding` |
| `metadata.name` | yes | Name of this binding. |

`metadata.name` matches `[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?`.

## Spec

| Field | Required | Meaning |
|---|---|---|
| `server` | yes | `metadata.name` of the server to realize. |
| `provider` | yes | `aws`, `azure`, or `vmware`. |
| `location` | yes | Same location as the matching NetworkBinding. |
| `realize` | yes | Map from server functions to provider resource kinds. |
| `aws` | when `provider` is `aws` | EC2 machine settings. |
| `azure` | when `provider` is `azure` | Azure VM settings. |
| `vmware` | when `provider` is `vmware` | vSphere machine settings. |

The block that matches `provider` is required. The other provider blocks are absent.

## `realize` keys

| Key | Realizes |
|---|---|
| `server` | The guest. |
| `interface` | Each server interface. |
| `public` | Each interface with `public: true`. |

## AWS

`location` is the region. `realize.server` is `instance`, `realize.interface` is `network-interface`, and `realize.public` is `elastic-ip`.

| Field | Required | Meaning |
|---|---|---|
| `aws.instanceType` | yes | EC2 instance type, for example `t3.micro`. |
| `aws.ami` | one of `ami`, or `amiNameFilter` with `amiOwner` | AMI id in this region. |
| `aws.amiNameFilter` | one of `ami`, or `amiNameFilter` with `amiOwner` | Name pattern of the AMI to use. `*` is a wildcard. Terraform selects the newest match in `location`. `ami_name_filter` is the same field. |
| `aws.amiOwner` | with `amiNameFilter` | Account that owns the AMI, for example `801119661308`. Quote the value when it has a leading zero. `ami_owner` is the same field. |
| `aws.keyName` | no | Name of an existing EC2 key pair. Build does not use this field. It generates a key pair for the range, imports the public key into EC2, and uses that pair for every server. |
| `aws.rootVolume.sizeGiB` | yes | Root volume size in GiB. |
| `aws.rootVolume.type` | yes | EBS type, for example `gp3`. |
| `aws.iamInstanceProfile` | no | Existing instance profile name. |
| `aws.securityGroupNames` | no | Existing security groups, attached beside the groups the network filters compile to. When the interface has no effective filters and this field is omitted, the compiler creates one group named for the server. That group allows all egress and no inbound traffic. When effective filters exist, the compiler does not create that default group. |

An explicit interface address becomes the private IP. `auto` leaves the address to the compiler, then to the subnet allocator. `public: true` allocates an elastic IP on an interface whose segment exposure is `internet`. `bootstrap.userData` names the bootstrap file. When it is omitted, the compiler uses `config/user_data/<server>.<provider>.*`. The compiler delivers that file's contents as instance user data.

## Azure

`location` is the region. `realize.server` is `virtual-machine`, `realize.interface` is `network-interface`, and `realize.public` is `public-ip`.

| Field | Required | Meaning |
|---|---|---|
| `azure.resourceGroup` | no | Resource group for the VM. When omitted, the compiler uses `azure.resourceGroup` from the NetworkBinding. |
| `azure.size` | yes | VM size, for example `Standard_B2s`. |
| `azure.image` | one of `image`, `imageId`, or `imagePublisher` with `imageOffer` and `imageSku` | Marketplace image: `publisher`, `offer`, `sku`, and `version`. |
| `azure.imageId` | one of `image`, `imageId`, or `imagePublisher` with `imageOffer` and `imageSku` | Resource id of a custom image. |
| `azure.imagePublisher` | with `imageOffer` and `imageSku` | Marketplace publisher, for example `Canonical`. `image_publisher` is the same field. Terraform selects the newest version in `location`. |
| `azure.imageOffer` | with `imagePublisher` and `imageSku` | Marketplace offer, for example `0001-com-ubuntu-server-jammy`. `image_offer` is the same field. |
| `azure.imageSku` | with `imagePublisher` and `imageOffer` | Marketplace SKU, for example `22_04-lts`. `image_sku` is the same field. |
| `azure.osDisk.sizeGiB` | yes | OS disk size in GiB. |
| `azure.osDisk.storageAccountType` | yes | Disk sku, for example `Premium_LRS`. |
| `azure.zone` | no | Availability zone. |
| `azure.adminPasswordSecret` | no | Name of a secret holding an admin password. v0.1 login uses `access.authorizedKeys` when this field is absent. |
| `azure.networkSecurityGroup` | no | Existing network security group. Valid when the server's interfaces have no effective filters. When effective filters exist, this field is absent and the compiler's merged group is the NIC group. When there are no filters and this field is omitted, the compiler creates one group named for the server. That group allows all outbound traffic and no inbound traffic. |

`access.username` is the admin user name. The authorized keys are installed for that user. An explicit interface address is a static private IP. `auto` is a dynamic private IP chosen from the subnet. `public: true` creates a public IP on an interface whose segment exposure is `internet`. `bootstrap.userData` names the bootstrap file. When it is omitted, the compiler uses `config/user_data/<server>.<provider>.*`. The compiler delivers that file's contents as VM custom data.

## VMware

`location` matches the NetworkBinding site. `realize.server` is `virtual-machine` and `realize.interface` is `nic`. vSphere has no public-address resource, so `realize` omits `public`, and an interface with `public: true` makes this binding invalid.

| Field | Required | Meaning |
|---|---|---|
| `vmware.datacenter` | no | Datacenter. When omitted, the compiler uses `vmware.datacenter` from the NetworkBinding. |
| `vmware.cluster` | one of `cluster`, `host` | Cluster that will run the VM. |
| `vmware.host` | one of `cluster`, `host` | Standalone host that will run the VM. |
| `vmware.datastore` | yes | Datastore for the VM files. |
| `vmware.template` | yes | Existing template to clone. |
| `vmware.folder` | no | VM folder. |
| `vmware.cpu` | no | vCPU count. When omitted, the template value is kept. |
| `vmware.memoryMiB` | no | Memory in MiB. When omitted, the template value is kept. |
| `vmware.disk.sizeGiB` | no | System disk size in GiB. When omitted, the template disk size is kept. |
| `vmware.dns` | no | DNS server addresses written by Linux guest customization. |

The compiler fills guest customization from the network. Each NIC's port group is the NetworkBinding port group for that segment. The address, netmask, and gateway come from the interface address and the segment. The guest hostname is `metadata.name` of the server. v0.1 does not deliver the `bootstrap.userData` file. The template already contains the authorized keys and the rest of the guest setup.

## Examples

These bindings are alternatives for [tmp/lab.server.yaml](../tmp/lab.server.yaml). Each one pairs with the NetworkBinding of the same provider.

- [tmp/lab.server-binding.aws.yaml](../tmp/lab.server-binding.aws.yaml)
- [tmp/lab.server-binding.azure.yaml](../tmp/lab.server-binding.azure.yaml)
- [tmp/lab.server-binding.vmware.yaml](../tmp/lab.server-binding.vmware.yaml)

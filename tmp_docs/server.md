# Server

A Server is one guest attached to a [Network](network.md). It names segments. The [NetworkBinding](network-binding.md) realizes each segment as a subnet or a port group, and a [ServerBinding](server-binding.md) places this guest there.

The same Server document can be bound to AWS, Azure, or VMware. Instance type, image, disk, and placement belong to the ServerBinding.

## Envelope

| Field | Required | Meaning |
|---|---|---|
| `apiVersion` | yes | `v0.1` |
| `kind` | yes | `Server` |
| `metadata.name` | yes | Name of this server. A ServerBinding refers to this name. The guest hostname is this name. |

`metadata.name` matches `[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?`.

## Spec

| Field | Required | Meaning |
|---|---|---|
| `network` | yes | `metadata.name` of the network. |
| `access` | yes | Login identity for the guest. |
| `interfaces` | yes | One or more attachments to segments. The first entry is the primary interface. |
| `bootstrap` | no | Guest bootstrap file. Delivery depends on the ServerBinding provider. |
| `provisioning` | no | Ordered steps run on the guest after it accepts SSH. |

### Access

v0.1 describes a Linux guest.

| Field | Required | Meaning |
|---|---|---|
| `access.username` | yes | Account name on the guest. |
| `access.authorizedKeys` | yes | One or more SSH public keys. The document holds public keys only. |

### Interfaces

| Field | Required | Meaning |
|---|---|---|
| `interfaces[].name` | yes | Unique on this server. |
| `interfaces[].segment` | yes | Segment in `network`. This is the attachment. |
| `interfaces[].address` | yes | A host address inside that segment, or `auto`. |
| `interfaces[].public` | no | `true` requests a public address. Legal only when the segment's zone exposure is `internet`. |
| `interfaces[].filters` | no | Filter names on this interface, in addition to the filters named by its segment. |

A name in `filters` is a filter on `network`. The effective set and the perimeter are defined in [Network](network.md). The NetworkBinding realizes that set.

### Bootstrap

| Field | Required | Meaning |
|---|---|---|
| `bootstrap.userData` | yes, when `bootstrap` is set | File name of the guest bootstrap, including its extension. |

The value is a file name such as `app-1.ps1`. It has an extension and no path separator. The file lives in [tmp/user-data](../tmp/user-data). The compiler reads that file and hands the contents to the provider.

AWS delivers the file contents as instance user data. Azure delivers them as custom data. VMware v0.1 sets the guest address and hostname through guest customization and does not deliver `userData`. A template used on VMware already contains the guest setup.

```yaml
bootstrap:
  userData: app-1.ps1
```

### Provisioning

`provisioning` is a list of steps. The provisioner runs them in order after `bootstrap` and after the guest accepts SSH for `access.username`. Each step has a `type` of `ansible` or `python`.

An `ansible` step runs one role against the guest. Several roles are several steps, in list order.

| Field | Required | Meaning |
|---|---|---|
| `role` | yes | Ansible role name. A namespace prefix is written `namespace.role`, for example `P4T12ICK.common`. |
| `vars` | no | Mapping of variable names to values passed to that role. |

A `python` step runs one script on the guest with `python3`, as `access.username`. `source` is `local` or `remote`.

| Field | Required | Meaning |
|---|---|---|
| `source` | yes | `local` or `remote`. |
| `file` | when `source` is `local` | File name, including its extension. No path separator. |
| `url` | when `source` is `remote` | `https` URL of the script. |

A local file lives in [tmp/python](../tmp/python). The provisioner copies it to the guest and runs it. A remote script is downloaded on the guest and then run.

```yaml
provisioning:
  - type: ansible
    role: P4T12ICK.common
    vars:
      common_username: ubuntu
      common_authorizedKeys:
        - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKeyForLabSpecOnly
  - type: python
    source: local
    file: configure.py
  - type: python
    source: remote
    url: https://example.com/setup.py
```

## Attachment

The server names a segment. It does not name a subnet id or a port group. The compiler joins the server to the NetworkBinding with the same provider and location as the ServerBinding, then places each interface in the resource that binding emitted for the segment:

| Provider | Segment becomes | Interface is placed in |
|---|---|---|
| `aws` | subnet | that subnet |
| `azure` | subnet | that subnet |
| `vmware` | port group | that port group |

The primary interface uses the default route of its segment. A further interface is attached to its segment and installs no default route.

## Addresses

The compiler reserves the segment router and any NAT address on that segment. An interface address is a remaining host address in the segment CIDR.

- `auto` takes the next free host address on that segment.
- An explicit address falls inside the segment CIDR.
- An address is unique across every interface in the network.
- The router and the NAT addresses are unavailable.

For [tmp/lab.network.yaml](../tmp/lab.network.yaml), `subnet-2` has router `10.0.1.1`. The address `10.0.1.10` is a valid primary address on that segment, and the default route follows `egress`.

## Example

See [tmp/lab.server.yaml](../tmp/lab.server.yaml).

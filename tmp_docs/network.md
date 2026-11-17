# Network

A Network is one IPv4 network. It owns an address space and the zones, segments, gateways, and reachability rules inside that space. Provider resources are declared in a [NetworkBinding](network-binding.md). A [Server](server.md) attaches to a segment of this network.

v0.1 is one address space, IPv4, exposures `internet`, `private`, and `isolated`, gateway types `internet` and `nat`, a perimeter of outside sources, and filters that allow flows. Deny rules, DNS, peering, IPv6, and a second network are later fields on this same kind.

## Envelope

| Field | Required | Meaning |
|---|---|---|
| `apiVersion` | yes | `v0.1` |
| `kind` | yes | `Network` |
| `metadata.name` | yes | Name of this network. A NetworkBinding and a Server refer to this name. |

`metadata.name` matches `[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?`. Zone, segment, and gateway names use the same pattern and are unique inside their own list. References are those names.

## Spec

| Field | Required | Meaning |
|---|---|---|
| `addressSpace` | yes | The only IPv4 CIDR this network owns. |
| `zones` | yes | Trust boundaries. Each segment belongs to one zone. |
| `segments` | yes | L3 domains. A binding realizes each one as a subnet, a VLAN, or both. |
| `gateways` | no | Functions at the edge of the address space. |
| `reachability` | no | Paths that leave the address space. |
| `perimeter` | no | Source prefixes that may enter from outside the address space. |
| `filters` | no | Named allow-lists. A segment or a server interface attaches them by name. |

## Address space

| Field | Required | Meaning |
|---|---|---|
| `cidr` | yes | IPv4 prefix, for example `10.0.0.0/16`. |

A network has one address space. Every segment CIDR is contained in it. A segment that sets `prefix` receives a CIDR of that length, packed into the address space in document order. Explicit CIDRs and allocated prefixes may appear on different segments. The resulting prefixes do not overlap.

```yaml
addressSpace:
  cidr: 10.0.0.0/16
```

## Zones

A zone is a trust boundary. Segments in the same zone share an exposure.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Unique among zones in the network. |
| `exposure` | yes | `internet`, `private`, or `isolated`. |

| Exposure | Meaning |
|---|---|
| `internet` | The segment may hold public addresses. An `internet` or `nat` gateway may attach here. |
| `private` | The segment has no public addresses. It leaves the address space only through a NAT gateway that lists it, and only when reachability selects that gateway. |
| `isolated` | The segment has no default route. Gateways do not attach here and do not serve it. |

```yaml
zones:
  - name: edge
    exposure: internet
  - name: app
    exposure: private
```

## Segments

A segment is one L3 domain inside a zone.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Unique among segments in the network. |
| `zone` | yes | Name of a zone. |
| `cidr` | one of `cidr`, `prefix` | Explicit IPv4 prefix inside the address space. |
| `prefix` | one of `cidr`, `prefix` | Prefix length. The compiler assigns a free CIDR of this length from the address space, in document order. |
| `filters` | no | Filter names applied to every interface in this segment. |

A segment sets `cidr` or `prefix`, and not both. `prefix` is an integer from 0 through 32, and it is longer than the address space prefix. `zone` names a zone in this network.

The compiler reserves addresses. The user does not set them.

- The first usable address of the segment is its router. For `10.0.0.0/24`, the router is `10.0.0.1`.
- A NAT gateway takes a further usable address from the segment named by its `attach`.

```yaml
segments:
  - name: subnet-1
    zone: edge
    cidr: 10.0.0.0/24
  - name: subnet-2
    zone: app
    cidr: 10.0.1.0/24
```

Allocated form:

```yaml
segments:
  - name: subnet-2
    zone: app
    prefix: 24
```

## Gateways

A gateway is a function at the edge of the address space. The binding chooses which provider resources realize each type. One function may become zero, one, or several resources.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Unique among gateways in the network. |
| `type` | yes | `internet` or `nat`. |
| `attach` | yes | Segment the function is placed on. |
| `serves` | for `nat` | Private segments that may egress through this NAT. |

`serves` is present on `nat` and absent on `internet`.

An `internet` gateway attaches to a segment whose zone exposure is `internet`. The compiler installs a default route on that segment through this gateway.

A `nat` gateway attaches to a segment whose zone exposure is `internet`. `serves` lists one or more segments whose zone exposure is `private`. Names in `serves` are unique on that gateway. The NAT address is allocated from the attach segment, after that segment's router address. The NAT's outside path uses an `internet` gateway attached to the same segment. A private segment receives a default route through this NAT only when a reachability entry selects it.

```yaml
gateways:
  - name: internet
    type: internet
    attach: subnet-1
  - name: egress
    type: nat
    attach: subnet-1
    serves: [subnet-2]
```

## Reachability

A reachability entry is a path that leaves the address space. v0.1 uses it to let a private segment egress through a named NAT gateway. Routes between segments inside the network are a property of the network, and they are not written as reachability entries.

| Field | Required | Meaning |
|---|---|---|
| `from` | yes | Source segment. |
| `to` | yes | `internet` in v0.1. |
| `via` | yes | Gateway that carries this path. |

Rules:

- `from` names a segment in this network.
- When `from` is in an `internet` zone, `via` is an `internet` gateway whose `attach` is that same segment.
- When `from` is in a `private` zone, `via` is a `nat` gateway whose `serves` includes that segment.
- When `from` is in an `isolated` zone, the entry is invalid.
- Two entries with the same `from` and `to` are invalid.

```yaml
reachability:
  - from: subnet-2
    to: internet
    via: egress
```

## Perimeter

A perimeter is the set of source prefixes outside the address space that may enter an `internet` segment. It is the network-level IP restriction. It names sources, not ports. Ports belong to a filter.

| Field | Required | Meaning |
|---|---|---|
| `sources` | yes | One or more IPv4 prefixes. |

Rules:

- Each prefix lies outside the address space. `0.0.0.0/0` is valid and admits every outside source.
- A prefix contained in the address space is invalid.
- Two copies of the same prefix are invalid.
- The perimeter applies to ingress into a segment whose zone exposure is `internet`. Private and isolated segments keep their ingress sources as written.
- The compiler intersects each ingress rule's `sources` with the address space plus `perimeter.sources`. A source inside the address space stays. A source outside the address space becomes its overlap with the perimeter. An empty overlap is dropped.
- When `perimeter` is omitted, ingress sources are used as written.

```yaml
perimeter:
  sources:
    - 203.0.113.10/32
```

The perimeter is a constraint on filters. It has no `realize` key. The compiler writes the intersected sources into the provider group that realizes the filter.

## Filters

A filter is a named allow-list of flows. It is the generic form of a security group, a network security group, and a firewall rule set. The network document names the filter. A segment or a server interface attaches it by name. The [NetworkBinding](network-binding.md) chooses the provider resource.

v0.1 filters allow flows. A flow that no attached rule allows is denied. Return traffic for an allowed flow is allowed. The document does not write the return rule. Deny rules and rule priority are later fields.

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Unique among filters in the network. |
| `rules` | yes | One or more allow rules. |

| Rule field | Required | Meaning |
|---|---|---|
| `direction` | yes | `ingress` or `egress`. |
| `protocol` | yes | `tcp`, `udp`, `icmp`, or `any`. |
| `ports` | for `tcp` and `udp` | Ports. An entry is a number from 1 through 65535, or a string `low-high` whose ends are inclusive and ordered. |
| `sources` | for `ingress` | One or more IPv4 prefixes. |
| `destinations` | for `egress` | One or more IPv4 prefixes. |

`ports` is absent when `protocol` is `icmp` or `any`. `sources` is present on `ingress` and absent on `egress`. `destinations` is present on `egress` and absent on `ingress`.

Attachment:

- `segments[].filters` lists filters for every interface in that segment.
- A server interface lists more filters in [Server](server.md). The effective set is the union of the two lists, by name, once each.
- A flow is allowed when one rule in that set allows it.
- When the effective set is empty, the compiler uses the default group in [ServerBinding](server-binding.md): all egress, and no ingress.

```yaml
filters:
  - name: ssh
    rules:
      - direction: ingress
        protocol: tcp
        ports: [22]
        sources:
          - 0.0.0.0/0
      - direction: egress
        protocol: any
        destinations:
          - 0.0.0.0/0
```

On an `internet` segment, the perimeter narrows the `0.0.0.0/0` source before the binding emits the group. On a `private` segment, that source stays `0.0.0.0/0`.

## Routing

Every segment can route to every other segment. The compiler installs one route for the address space on each segment. v0.1 does not remove those routes.

Paths that leave the address space come from gateways and reachability:

- An `internet` gateway installs a default route on the segment it attaches to.
- A `nat` gateway installs a default route on a private segment only when a reachability entry selects that gateway for that segment.
- A private segment with no such entry has no default route.
- An `isolated` zone has no default route.

Derived for [tmp/lab.network.yaml](../tmp/lab.network.yaml):

| Segment | Router | Default route |
|---|---|---|
| `subnet-1` | `10.0.0.1` | `internet` |
| `subnet-2` | `10.0.1.1` | `egress`, because reachability selects it |

`egress` takes its own address in `10.0.0.0/24` and uses `internet` for its outside path. Both segments keep a route for `10.0.0.0/16`.

## Example

See [tmp/lab.network.yaml](../tmp/lab.network.yaml).

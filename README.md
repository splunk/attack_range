# Splunk Attack Range v6
![Attack Range Logo](docs/attack_range.png)

The Splunk Attack Range builds instrumented lab environments for detection development and testing. A range is described in a few provider-neutral YAML documents and realized on AWS, Azure, or VMware vSphere with Terraform.

> **Status:** v6 is a rewrite. The CLI can `plan`, `build`, `list`, and `destroy` the infrastructure of ranges. Provisioning the servers (Ansible roles and Python steps), attack simulation, the web app (`app/`), the REST API (`api/`), and the Docker setup (`docker/`) are not ported to the new code yet.

---

## Getting started

**Prerequisites**

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Terraform](https://developer.hashicorp.com/terraform/install) 1.10 or newer, installed separately (`uv sync` does not install it). `plan`, `build`, and `destroy` run it from your `PATH`, or from the path given with `--terraform`. Version 1.10 is the first that can lock S3 state without DynamoDB. On macOS: `brew tap hashicorp/tap && brew install hashicorp/tap/terraform`
- Credentials for your provider in the usual places: `~/.aws` or `AWS_*` for AWS, `az login` or `ARM_*` for Azure (the subscription is the one from `az account show`, unless `ARM_SUBSCRIPTION_ID` is set), `VSPHERE_SERVER`, `VSPHERE_USER`, and `VSPHERE_PASSWORD` for VMware

**Install**

```bash
git clone <repo-url>
cd attack_range
uv sync
```

**Run**

```bash
uv run attack-range plan tmp/ar_template      # show what would be created; registers nothing
uv run attack-range build tmp/ar_template     # register a new range, create it, and print its id
uv run attack-range update add <RANGE_ID> PATH       # merge changed or new documents and apply them
uv run attack-range update change <RANGE_ID> PATH    # apply a modified file or folder already in the range
uv run attack-range update remove <RANGE_ID> FILES   # remove config files, as shown by get, and apply
uv run attack-range list                      # show the ranges and their state
uv run attack-range get <RANGE_ID>            # show one range, its network, and its servers
uv run attack-range destroy <RANGE_ID>        # remove a range again (asks for confirmation)
uv run attack-range init                      # set or replace the stored user name and password
uv run attack-range upload azure VHD --region westeurope   # upload a .vhd and print its image id
```

`plan` and `build` take a template: a directory of range documents, or a single `.yaml` file that holds all documents separated by `---`. [`tmp/ar_template`](tmp/ar_template) is a Splunk server and a Windows server on AWS. Every `build` registers a new range under a fresh UUID, even from the same template, so one template can run several times. After `build`, the CLI prints the id and the private and public IP address of every server. `destroy` takes that id.

`update` takes that id and a file or directory of documents. A document with the same kind and name as one already in the range changes that document's parameters. A document that is not in the range yet is added. Documents the path does not mention stay as they are. When nothing changed, `update` does not run Terraform.

`get` takes that id and prints the range: its record, the network and servers from its documents, and the history of its states.

`upload azure` takes a `.vhd` file and a region. It creates a resource group, a storage account, and a managed image, named `<resource>-<id>-<user name>` like the other cloud resources. The storage account drops the hyphens so Azure accepts it. The command prints the image id to use as `azure.imageId`. The VHD must be a multiple of 512 bytes. `--os-type` defaults to `Linux` and `--generation` defaults to `V1`.

| Option | Command | Meaning |
|--------|---------|---------|
| `--provider aws\|azure\|vmware` | `plan`, `build` | Which bindings to use. Needed only when the template binds the network to more than one provider, like [`tmp`](tmp). |
| `--set NAME.PATH=VALUE` | `plan`, `build`, `update add` | Replace a field. Repeat the option for several fields. `NAME` is the document name, or `*` for every document of this provider that has the field. `VALUE` is YAML. |
| `--local-state` | `build` | Keep the Terraform state in the range folder instead of S3 or Azure Blob Storage. `destroy` uses the same choice. |
| `--terraform BIN` | `plan`, `build`, `update`, `destroy` | Terraform binary to run. Default: `terraform`. |
| `-y`, `--yes` | `destroy` | Skip the confirmation. Required when not running in a terminal. |
| `--all` | `list` | Include destroyed ranges. |

---

## The home folder and range states

The first run creates `~/.attack_range` (set `ATTACK_RANGE_HOME` to use another folder) and asks for a user name and a password. Both are stored in `config.yaml` and reused after that. `attack-range init` asks again and replaces both. `$PASSWORD$` uses the new password the next time a range is loaded. The file is written so only the owner can read it. The user name is a lowercase letter followed by lowercase letters, digits, or hyphens, at most 32 characters, and it does not end with a hyphen. The password is at least 8 characters and includes a letter, a number, and a special character. A config that already has a user name asks for the password the next time attack-range runs. Outside a terminal, write `user_name` and `password` in that file before running a command. A template may use `$USER$` and `$PASSWORD$` in a document or a user-data file. Loading the range replaces them with these config values. The template files keep the tokens.

Cloud resources are named `<resource>-<first group of the range id>-<user name>`, for example `win-e6fffcb8-ada`. A range keeps the user name it was built with, so editing `config.yaml` later does not rename resources that already exist. `plan` has no range id yet; it keeps a preview id in the plan folder so the names in a plan stay stable, and `build` uses the range's own id. A name that a provider cannot accept at full length keeps the id prefix and drops the user name, which is what happens to a Windows computer name.

```text
~/.attack_range/
├── config.yaml                 # user_name and password, asked for the first time attack-range runs
├── plans/
│   └── <name>-<provider>/      # Terraform code of `plan`, with local state and a preview id
└── ranges/
    └── <range id>/
        ├── range.yaml          # name, user name, provider, location, template path, state, outputs, history
        ├── documents/          # copy of the template's .yaml files and the user-data files they use
        ├── keys/               # SSH key pair; the private key stays here
        ├── wireguard/          # WireGuard client.conf for an AWS or Azure range
        └── terraform/          # generated Terraform code
```

`build` copies the template into `documents/`, so later edits to the template don't change a running range. `destroy` reads the copy.

An AWS build generates a 2048-bit RSA key pair in `keys/` and imports the public key as an EC2 key pair named `key-<range id prefix>-<user name>`. Every server in the range uses that pair, including Windows. `destroy` deletes the EC2 key pair with the rest of the range. The private key stays in `keys/`.

An AWS or Azure build also creates a WireGuard gateway on the internet subnet. The guest is the Server and ServerBinding documents in `attack_range_infrastructure/config/wireguard/`. After Terraform finishes, Ansible provisions that gateway and prints the client configuration. Copy it into the WireGuard app and enable the tunnel, then press Enter. The build then provisions the other servers over the VPN. The client configuration is also written to `wireguard/client.conf`. `update add` and `update change` keep the existing WireGuard configuration. They check that the tunnel reaches the gateway and ask you to enable the existing tunnel when it does not. Ansible then runs only for servers whose document or binding was added or changed. `update change` takes a modified file or folder, and every document in it must already be in the range. `update remove` takes a comma-separated list of those config files and deletes them before applying. A server binding is removed only together with its server, and a server is removed only together with its binding. `get` prints the public endpoint and the path of the file.

Each range moves through these states, and `range.yaml` records every change with its time and error:

```mermaid
stateDiagram-v2
    [*] --> created: build
    created --> building
    created --> build_failed: template copy failed
    building --> built
    building --> build_failed
    built --> building
    built --> destroying: destroy
    build_failed --> building
    build_failed --> destroying: destroy
    destroying --> destroyed
    destroying --> destroy_failed
    destroy_failed --> destroying: destroy
    destroyed --> [*]
```

A failed or interrupted build ends in `build_failed` and can still be destroyed. A failed destroy can be run again. After a successful destroy, the record and documents stay, and only `terraform/` is deleted. `list` hides destroyed ranges unless you pass `--all`.

Destroyed ranges are kept for 30 days. After that, the next command (any of `plan`, `build`, `destroy`, or `list`) deletes their record and documents, and says so on stderr. Ranges in any other state are never deleted.

---

## Describing a range

A template holds four kinds of documents (API version `v0.1`), either in the `*.yaml` and `*.yml` files of a directory or in one file:

| Kind | Describes |
|------|-----------|
| `Network` | Address space, zones (`internet`, `private`, `isolated`), segments, internet and NAT gateways, reachability, the perimeter, and filters (allow-lists of flows). Provider neutral. |
| `NetworkBinding` | How one provider realizes the network, for example a VPC with subnets and security groups on AWS. |
| `Server` | One guest: login, interfaces with their segment and address, optional bootstrap file, and provisioning steps. Provider neutral. |
| `ServerBinding` | How one provider realizes the server, for example instance type, AMI, and root volume on AWS. |

When `bootstrap.userData` is omitted, a server uses `attack_range_infrastructure/config/user_data/<server>.<provider>.*` when that file exists. A set name is read from `user-data/` in the template directory, except a name such as `win.ps1`, which uses `config/user_data/win.<provider>.ps1`. One directory can hold bindings for several providers next to each other. Each command uses the bindings of one provider.

Example network ([`tmp/ar_template/ar.network.yaml`](tmp/ar_template/ar.network.yaml), shortened):

```yaml
apiVersion: v0.1
kind: Network
metadata:
  name: ar
spec:
  addressSpace:
    cidr: 10.0.0.0/16
  zones:
    - name: edge
      exposure: internet
    - name: private
      exposure: private
  segments:
    - name: public
      zone: edge
      cidr: 10.0.1.0/24
    - name: mgmt
      zone: private
      cidr: 10.0.2.0/24
  gateways:
    - name: internet
      type: internet
      attach: public
    - name: egress
      type: nat
      attach: public
      serves: [mgmt]
  reachability:
    - from: mgmt
      to: internet
      via: egress
```

**Tags.** A NetworkBinding can set tags for every resource of the range, for example to meet a tagging policy of the account:

```yaml
kind: NetworkBinding
spec:
  network: ar
  provider: aws
  location: eu-central-1        # becomes the provider region
  tags:
    splunkit_environment_type: non-prd
    splunkit_data_classification: private
```

| Provider | How the tags are applied |
|----------|--------------------------|
| AWS | `default_tags` of the `aws` provider, so every taggable resource gets them |
| Azure | Merged into the `tags` of every taggable resource (resource group, virtual network, public IPs, NAT gateways, NSGs, NICs, VMs) |
| VMware | Not supported in v0.1; a VMware binding with tags is rejected |

Keys are 1 to 128 characters and values at most 256. Keys must not start with `aws:` or `azure`, must not contain `< > % & \ ? /`, and must not be `Name` or `attack-range`, which Attack Range sets itself.

The documents are validated before anything runs: every reference must exist, addresses must lie inside their segment, every server needs a binding for the chosen provider, and all bindings must use the same location.

---

## Terraform state

| Provider | State is stored in |
|----------|--------------------|
| AWS | S3 bucket `attack-range-tfstate-<account id>-<region>`: versioned, encrypted, public access blocked, locked with S3 lock files |
| Azure | Storage account `artfstate<hash>` in resource group `attack-range-tfstate`, container `tfstate`, locked with blob leases |
| VMware | `terraform.tfstate` in `ranges/<range id>/terraform/` |

The bucket or storage account is shared by all ranges in an account (or subscription) and region. It is created on first use and is never deleted, including by `destroy`. Each range gets its own key, `<prefix>/<range id>/terraform.tfstate`, so ranges built from the same template never share state. Existing local state is copied into the remote store on the next run. `plan` always uses local state in `plans/` and does not touch the remote store.

| Variable | Overrides |
|----------|-----------|
| `ATTACK_RANGE_STATE_PREFIX` | Key prefix (default `attack-range`) |
| `ATTACK_RANGE_STATE_BUCKET` | S3 bucket name |
| `ATTACK_RANGE_STATE_RESOURCE_GROUP` | Azure resource group |
| `ATTACK_RANGE_STATE_STORAGE_ACCOUNT` | Azure storage account |

---

## Code layout

The code follows a clean architecture. Use cases depend only on abstract ports, and the CLI wires the concrete implementations together with [dependency-injector](https://python-dependency-injector.ets-labs.org/).

| Package | Contents |
|---------|----------|
| [`attack_range/domain`](attack_range/domain) | Pydantic models of the four document kinds, `RangeRecord`, and the `RangeState` state machine |
| [`attack_range/application`](attack_range/application) | `CyberRange` and its consistency checks, and the ports `CyberRangeRepository`, `RangeStore`, `RangeDocuments`, `Provisioner`, and `ProvisionLog` |
| [`attack_range/use_cases`](attack_range/use_cases) | `Plan`, `Build`, `Destroy`, `ListRanges`, and `PruneRanges`, with their input and output DTOs and output boundaries |
| [`attack_range_infrastructure`](attack_range_infrastructure) | The home folder, `FileCyberRangeRepository` (reads templates), `YamlRangeStore` and `FileRangeDocuments` (keep ranges in the home folder), and `TerraformProvisioner` with one renderer per provider and the state backends |
| [`cli`](cli) | Argument parsing, the dependency-injection container, and the console presenters |
| [`tests`](tests) | Unit tests, plus `terraform validate` of the generated code |

A new provisioner, for example one that generates Bicep, implements `Provisioner` (`render`, `plan`, `apply`, `destroy`, `clean`) and is registered in [`cli/container.py`](cli/container.py). The same goes for keeping range records in a database instead of YAML files: implement `RangeStore` (`create`, `get`, `update`, `list`, `delete`), and `RangeDocuments` if the documents should move too, and swap them in the container.

**Run the tests**

```bash
uv run pytest
```

The tests use a temporary home folder and never touch `~/.attack_range`. The `terraform validate` tests download the Terraform providers and are skipped when Terraform is not installed.

---

## Support
Please use the [GitHub issue tracker](https://github.com/splunk/attack_range/issues) to submit bugs or request features.

If you have questions or need support, you can:

* Join the [#security-research](https://splunk-usergroups.slack.com/archives/C1S5BEF38) room in the [Splunk Slack channel](http://splunk-usergroups.slack.com)
* Post a question to [Splunk Answers](http://answers.splunk.com)
* If you are a Splunk Enterprise customer with a valid support entitlement contract and have a Splunk-related question, you can also open a support case on the https://www.splunk.com/ support portal

---

## Contributing
We welcome feedback and contributions from the community! Please see our [contribution guidelines](docs/CONTRIBUTING.md) for more information on how to get involved.

---

## Author
* [Jose Hernandez](https://twitter.com/_josehelps)
* [Patrick Bareiß](https://twitter.com/bareiss_patrick)

## Contributors
* [Bhavin Patel](https://twitter.com/hackpsy)
* [Rod Soto](https://twitter.com/rodsoto)
* Russ Nolen
* Phil Royer
* [Joseph Zadeh](https://twitter.com/JosephZadeh)
* Rico Valdez
* [Dimitris Lambrou](https://twitter.com/etz69)
* [Dave Herrald](https://twitter.com/daveherrald)
* Ignacio Bermudez Corrales
* Peter Gael
* Josef Kuepker
* Shannon Davis
* [Mauricio Velazco](https://twitter.com/mvelazco)
* [Teoderick Contreras](https://twitter.com/tccontre18)
* [Lou Stella](https://twitter.com/ljstella)
* [Christian Cloutier](https://github.com/ccl0utier)
* Eric McGinnis
* [Micheal Haag](https://twitter.com/M_haggis)
* Gowthamaraj Rajendran
* [Christopher Caldwell](https://github.com/cudgel)
* [Zachary Christensen](https://github.com/ZachTheSplunker)
* [JerinSaji0](https://github.com/JerinSaji0)
* [Michal Cichorz](https://github.com/cichyx96)

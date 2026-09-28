# Configuration

Attack Range is driven by YAML configuration files. Each **running** or **in-progress** range has a config file in `config/` named by its attack range ID (e.g. `config/<uuid>.yml`). Configs are created from **templates** in `templates/{aws,azure,gcp}/`.

## Config file structure

A typical config has:

- **general** — Passwords, cloud provider, naming, IP whitelist, description, and internal fields (e.g. `attack_range_id`, `status`, `key_name`, `template_path`).
- **Provider block** — `aws`, `azure`, or `gcp` with region, keys, tags, etc.
- **attack_range** — List of servers (Splunk, Windows, Linux, Kali, Zeek, etc.) with instance types, IP octets, and **roles**.

Example (minimal):

```yaml
general:
  attack_range_password: "changeme123!"
  cloud_provider: aws
  attack_range_name: ar
  ip_whitelist: 0.0.0.0/0
  description: Minimal AWS deployment with Splunk only

aws:
  region: eu-central-1

attack_range:
  - name: splunk
    ami_name_filter: ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*
    ami_owner: "099720109477"
    instance_type: t3.xlarge
    ip_last_octet: 10
    linux: true
    user_name: ubuntu
    roles:
      - role: P4T12ICK.ludus_ar_splunk
        vars:
          ludus_ar_splunk_password: "changeme123!"
```

## General section

| Field | Description |
|-------|-------------|
| `attack_range_password` | Master password used for Splunk, Windows/Linux accounts, and role vars when not overridden. |
| `cloud_provider` | `aws`, `azure`, or `gcp`. |
| `attack_range_name` | Short name prefix for resources (e.g. `ar`). |
| `ip_whitelist` | CIDR(s) allowed to reach certain resources (e.g. `0.0.0.0/0` for any). |
| `description` | Human-readable description of the range. |
| `attack_range_id` | Unique ID (UUID) for this range; set when creating from template. |
| `key_name` | SSH key name in the cloud (often same as `attack_range_id`). |
| `name` / `template_path` | Template name/path (set when creating from template). |
| `status` | Internal: `build_vpn`, `wait_for_vpn`, `build_lab`, `running`, `error`, `destroying`, etc. |

Passwords in role `vars` (e.g. `ludus_ar_splunk_password`, `ar_guacamole_password`) override or complement the general password.

## Provider sections

### AWS (`aws`)

- `region` — e.g. `eu-central-1`.
- `private_key_path` — Path to the SSH private key (often under `ssh_keys/<attack_range_id>.key`).
- `ami_name_filter`, `ami_owner` — Used per server when not using a shared image.
- `aws_default_tags` — Optional tags applied to resources.

### Azure (`azure`)

- `location` — e.g. `West Europe`.
- `subscription_id` — Azure subscription ID.
- `image_publisher`, `image_offer`, `image_sku` — Defined per server in the template.

### GCP (`gcp`)

- Region/project and image settings as defined in the template and Terraform variables.

## Attack range (servers)

Each entry under `attack_range` is a machine:

| Field | Description |
|-------|-------------|
| `name` | Host name; used as Ansible inventory host and as simulation target. |
| `instance_type` | Cloud instance type (e.g. `t3.xlarge`, `Standard_D4s_v3`). |
| `ip_last_octet` | Last octet of the private IP (e.g. 10 → `10.0.2.10`, or `10.0.5.10` when `network: inside`). |
| `network` | Optional AWS subnet: `mgmt` (default, `10.0.2.0/24`), `inside` (`10.0.5.0/24` behind FTDv), `outside` (`10.0.4.0/24`), `diag` (`10.0.3.0/24`). |
| `linux` / `windows` | OS type. |
| `cisco_fmc` / `cisco_ftd` | AWS-only flags that deploy Cisco Secure Firewall Management Center or Threat Defense from Marketplace AMIs (multi-NIC for FTD, day-0 config, no generic Linux user-data). |
| `user_name` | SSH (Linux) or RDP (Windows) user. |
| `roles` | List of Ansible roles (and optional `vars`) applied to this server. |

Additional provider-specific fields (e.g. `ami_name_filter`, `ami_owner`, `ami_product_code`, `image_offer`) are set per server in templates.

## Where configs live

- **Templates:** `templates/aws/`, `templates/azure/`, `templates/gcp/` — Read-only; use to create a new range.
- **Active configs:** `config/<attack_range_id>.yml` — Created from a template at build start; updated with status, WireGuard config, sharing, etc.

The API and app always work with the config directory; the CLI uses `config/` and resolves `-c` to a path or to `config/<id>.yml`.

**Do not modify files in the `config/` folder manually.** The app and API create and update these files during build, destroy, share, and status changes. Editing them by hand can cause unintended side effects (e.g. out-of-sync state, failed operations, or duplicate or orphaned resources). Use the app, API, or CLI for all operations.

## Creating a config from a template

- **API:** `POST /attack-range/build` with `{"template": "aws/splunk_minimal_aws"}` (or `provider/name` / `name`). The server creates `config/<new_uuid>.yml` and starts the build.
- **CLI:** `python attack_range.py build -t aws/splunk_minimal_aws`. The CLI creates the config and runs the two-phase build.

## Environment and credentials

- **Docker:** Mount `~/.aws`, `~/.azure`, and/or `~/.config/gcloud` into the API and CLI containers so they can call cloud APIs and run Terraform.
- **API:** `GET /providers/check` returns which provider CLIs and credentials are available.

See [Templates](templates.md) for the list of built-in templates and their structure.

# Templates

Templates are YAML files that define an Attack Range layout: cloud provider, general settings, and the list of servers (Splunk, Windows, Linux, Kali, Zeek, etc.) with their roles. Each **build** starts from a template; a copy is saved as `config/<attack_range_id>.yml` and used for that range’s lifecycle.

## Where templates live

Templates are under **provider-specific** directories:

```
templates/
├── aws/
│   ├── splunk_minimal_aws.yml
│   ├── splunk_windows_aws.yml
│   ├── splunk_windows_kali_aws.yml
│   └── ...
├── azure/
│   ├── splunk_minimal_azure.yml
│   ├── splunk_windows_azure.yml
│   └── ...
└── gcp/
    ├── splunk_minimal_gcp.yml
    ├── splunk_windows_gcp.yml
    └── ...
```

The **template identifier** you use in the API or CLI can be:

- **Provider + name:** `aws/splunk_minimal_aws` (recommended)
- **Name only:** `splunk_minimal_aws` (searched across all provider dirs)
- **With extension:** `splunk_minimal_aws.yml`

## Built-in templates

Each template is a ready-to-build lab. Identifiers are `provider/name` (for example `aws/cisco_fmc_ftd_aws`). Exact instance types, images, and role vars are in the YAML; use `GET /templates/<provider>/<name>` to inspect.

### AWS (`templates/aws/`)

#### `splunk_minimal_aws`

Single Splunk Enterprise server. Use this as the smallest working range or as a starting point for a custom template.

#### `splunk_minimal_all_apps`

Same layout as `splunk_minimal_aws`, with a larger set of Splunk apps/TAs preinstalled (Windows, Sysmon, Unix, CIM, Content Update, Cisco Security Cloud, and others).

#### `splunk_linux_aws`

Splunk plus a Linux endpoint for testing Linux-based attacks. Forwarders send host data into Splunk.

#### `splunk_windows_aws`

Splunk plus a Windows endpoint for testing Windows-based attacks. Sysmon and the Windows TA are installed on the endpoint.

#### `splunk_windows_kali_aws`

Splunk, a Windows endpoint, and Kali Linux (Guacamole VNC to Kali). Use this when you want an attacker box in the same range as the victim.

#### `splunk_ad_aws`

Splunk, a Windows Active Directory domain controller, and a domain-joined Windows endpoint.

#### `splunk_es_aws`

Splunk with the Enterprise Security add-on for advanced security analytics.

#### `splunk_soar_aws`

Splunk plus a Splunk SOAR (Phantom) instance.

#### `splunk_zeek_windows_aws`

Splunk, a Zeek network sensor, and a Windows endpoint whose traffic is monitored by Zeek.

#### `cisco_fmc_ftd_aws` {#cisco_fmc_ftd_aws}

AWS-only lab: Splunk, Cisco Secure Firewall Management Center (FMCv), Threat Defense (FTDv), a Windows victim on the FTD inside network (`10.0.5.11`), and Kali.

The AWS account must already be subscribed to the Cisco FMCv and FTDv BYOL Marketplace listings. First boot plus FTD registration can take 45–90 minutes. Access:

- Splunk: `http://10.0.2.10:8000` (admin / `attack_range_password`)
- FMC: `https://10.0.2.20` (admin / `attack_range_password`)
- Windows RDP: `10.0.5.11` (Administrator / `attack_range_password`)

**Logging to Splunk is not configured automatically.** Splunk is built first with syslog listeners (UDP/TCP **514** for FMC audit, sourcetype `cisco:fmc:audit`; UDP/TCP **1514** for FTD events, sourcetype `cisco:ftd:syslog`) and the Cisco Security Cloud TA. After the range is **running**, send FMC/FTD logs to Splunk in the FMC GUI:

1. Open **System > Configuration > Audit Log**. Enable syslog to Splunk at `10.0.2.10` UDP **514** (facility AUDIT, tag `FMC-AUDIT-LOG`).
2. Open **Integrations > Splunk** and create a profile that sends events to `10.0.2.10` UDP **1514**.
3. **Deploy** the changes to FTD.

Search in Splunk:

- Audit logs: `index=syslog sourcetype=cisco:fmc:audit`
- Firewall events: `index=syslog sourcetype=cisco:ftd:syslog`

### Azure (`templates/azure/`)

| Template | Description |
|----------|-------------|
| `splunk_minimal_azure.yml` | Single Splunk server. |
| `splunk_linux_azure.yml` | Splunk plus a Linux endpoint for testing Linux-based attacks. |
| `splunk_windows_azure.yml` | Splunk plus a Windows endpoint for testing Windows-based attacks. |
| `splunk_full_azure.yml` | Splunk plus Linux and Windows endpoints. |
| `splunk_ad_azure.yml` | Splunk, Windows Active Directory domain controller, and a domain-joined Windows endpoint. |
| `splunk_es_azure.yml` | Splunk with the Enterprise Security add-on. |

### GCP (`templates/gcp/`)

| Template | Description |
|----------|-------------|
| `splunk_minimal_gcp.yml` | Single Splunk server. |
| `splunk_linux_gcp.yml` | Splunk plus a Linux endpoint for testing Linux-based attacks. |
| `splunk_windows_gcp.yml` | Splunk plus a Windows endpoint for testing Windows-based attacks. |
| `splunk_ad_gcp.yml` | Splunk, Windows Active Directory domain controller, and a domain-joined Windows endpoint. |
| `splunk_es_gcp.yml` | Splunk with the Enterprise Security add-on. |
| `splunk_zeek_windows_gcp.yml` | Splunk, Zeek network monitoring, and a Windows endpoint. |

## Template structure

A template has the same layout as a [configuration](configuration.md) file:

1. **general** — `attack_range_password`, `cloud_provider`, `attack_range_name`, `ip_whitelist`, `description`. No `attack_range_id` or `status` (those are set when creating a range from the template).

2. **Provider block** — Either `aws`, `azure`, or `gcp` with region, tags, and (for AWS) optional key/image defaults.

3. **attack_range** — List of servers. Each server has:
   - `name`, `instance_type`, `ip_last_octet`, `linux` or `windows` (or `cisco_fmc` / `cisco_ftd` on AWS), `user_name`
   - Provider-specific image/AMI fields (e.g. `ami_name_filter`/`ami_owner` for AWS, `image_publisher`/`image_offer`/`image_sku` for Azure)
   - **roles** — Ansible roles (and `vars`) applied to that host (e.g. `P4T12ICK.ludus_ar_splunk`, `P4T12ICK.ar_cisco_fmc`, `P4T12ICK.ar_guacamole`, `P4T12ICK.ludus_ar_windows`, `P4T12ICK.ar_kali`)

## Listing and fetching templates

- **API**
  - `GET /templates` — List all templates (optionally with provider availability).
  - `GET /templates/<provider>/<name>` — Full content of one template (YAML as JSON).
- **CLI** — No direct “list templates” command; use the templates dir or the API. Build references a template by name: `build -t aws/splunk_minimal_aws`.

## Creating a custom template

1. Copy an existing template from `templates/<provider>/` (e.g. `splunk_windows_aws.yml`).
2. Put it in the same provider directory (or a custom location and reference by path if your workflow supports it).
3. Edit:
   - **general** — description, password, whitelist.
   - **attack_range** — add/remove servers, change instance types, adjust roles and vars.
4. Do **not** set `attack_range_id` or `status`; those are set when a range is created from the template.
5. Use the new file as the template in the app or API (e.g. `build -t aws/my_custom_template`).

Templates are read at build start; the saved config in `config/<attack_range_id>.yml` is the one updated with status, WireGuard, and sharing. See [Configuration](configuration.md) and [Ansible Roles](ansible-roles.md) for role names and variables.

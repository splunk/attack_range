# Ansible Roles

Attack Range uses **Ansible** to configure every server in your range: the VPN router and all lab hosts (Splunk, Windows, Linux, Kali, etc.). Which software and behavior each host gets is defined by **roles**. You choose those roles in a **template** (and thus in the generated config). Crucially, **you can use any Ansible Galaxy role** in a template to define a new configuration—not only the ones shipped with Attack Range.

## Using any Ansible Galaxy role in a template

Templates define the layout of your range. Under `attack_range`, each server has a **roles** list. Every role you list there is:

1. **Installed automatically** — Before any playbook runs, Attack Range extracts all role names from the config and runs `ansible-galaxy install <role_name>` for each. So any role that exists on [Ansible Galaxy](https://galaxy.ansible.com/) can be used.
2. **Applied at build time** — The main lab playbook is generated from your config. Each server gets a play that runs exactly the roles you attached to it, in order, with any variables you passed.

So if you want to add a custom stack (e.g. a different Splunk app, a monitoring role, or a security tool), add the Galaxy role name to the **roles** list of the right server in your template and build from that template. No need to modify Attack Range code.

### Role name format

Use the **Galaxy role name** as it appears on Ansible Galaxy. That is usually `namespace.role_name` (e.g. `geerlingguy.nginx`, `P4T12ICK.ludus_ar_splunk`). The same format is used when you run `ansible-galaxy install namespace.role_name`.

### Declaring roles in a template

In the template (and thus in the config), each server is a list entry under `attack_range`. The **roles** key is a list. You can use either of these forms:

**Role name only (string):**

```yaml
attack_range:
  - name: myserver
    instance_type: t3.medium
    ip_last_octet: 20
    linux: true
    user_name: ubuntu
    roles:
      - geerlingguy.docker
      - some_namespace.some_role
```

**Role with variables (dictionary):**

```yaml
attack_range:
  - name: splunk
    ...
    roles:
      - role: P4T12ICK.ludus_ar_splunk
        vars:
          ludus_ar_splunk_password: "MySecurePass"
      - role: geerlingguy.nginx
        vars:
          nginx_http_port: 8080
```

- **role** — The Galaxy role name (required in the dict form).
- **vars** — Optional variables passed to that role for this host. Follow the role’s documentation on variable names and values.
- **inventory_name** — Optional. If set, this role is applied to the host group with that name instead of the server’s `name`. Used when one role expects a specific group name in the inventory.

You can mix string and dict entries in the same **roles** list. Multiple roles on the same server run in the order listed.

### Example: defining a new configuration with Galaxy roles

1. Copy an existing template from `templates/<provider>/` (e.g. `splunk_minimal_aws.yml`).
2. Add or replace roles under the server(s) you want to change. Use any Galaxy role names.
3. For each role that needs options, use the dict form and set **vars** according to the role’s docs.
4. Save the template (e.g. as `templates/aws/my_custom_range.yml`) and build from it via the app or API (e.g. template `aws/my_custom_range`).

At build time, Attack Range will install every listed Galaxy role and run them on the matching hosts. No extra steps are required.

## How roles are installed and run

- **Source of truth:** The config file (created from your template) in `config/<attack_range_id>.yml`. Its `attack_range` section lists servers and their **roles**.
- **Installation:** Before the VPN and lab playbooks run, the controller scans `attack_range` for all role names (from both `role: name` and plain `name` in the list) and runs `ansible-galaxy install` for each. So only roles referenced in your config are installed.
- **Execution:** The lab playbook (`lab.yaml`) is generated from the same config: one play per host (or per `inventory_name` group), with that host’s roles and vars. So the exact roles and variables you put in the template are what run on each machine.

This is why **any** Galaxy role can define your configuration: if it’s in the template’s **roles** list, it gets installed and executed.

## Local development with a role checkout

When developing or testing an Ansible role locally, you can point Attack Range at a directory on disk instead of downloading from Ansible Galaxy. Templates still use the normal Galaxy role name (e.g. `P4T12ICK.ludus_ar_splunk`); only the install source changes.

### `ATTACK_RANGE_LOCAL_ROLES`

Set this environment variable to a JSON object mapping Galaxy role names to **local filesystem paths** (paths must exist where Attack Range runs):

```bash
export ATTACK_RANGE_LOCAL_ROLES='{"P4T12ICK.ludus_ar_splunk": "/local_roles/ludus_ar_splunk"}'
```

Keys must match the role name in your template exactly. During build, overridden roles are installed with `ansible-galaxy install <path>,<role_name>` instead of downloading from Galaxy. Each build uses `--force`, so edits to your mounted checkout are picked up on the next run.

### Docker Compose workflow

1. Clone your role repo on the host (e.g. `~/projects/ludus_ar_splunk`).
2. Mount it into the CLI or API container and set `ATTACK_RANGE_LOCAL_ROLES`. Example volume in `docker/docker-compose.yml` or a `docker-compose.override.yml`:

   ```yaml
   volumes:
     - ~/projects/ludus_ar_splunk:/local_roles/ludus_ar_splunk:ro
   environment:
     - ATTACK_RANGE_LOCAL_ROLES={"P4T12ICK.ludus_ar_splunk": "/local_roles/ludus_ar_splunk"}
   ```

   Paths in `ATTACK_RANGE_LOCAL_ROLES` are **container paths** (`/local_roles/...`), not host paths. See `docker/.env.example` for a template.

3. Build as usual:

   ```bash
   docker compose --profile cli -f docker/docker-compose.yml run --rm attack_range build -t aws/splunk_minimal_aws
   ```

Roles not listed in `ATTACK_RANGE_LOCAL_ROLES` continue to install from Ansible Galaxy.

## Cisco FMC Galaxy role

The `P4T12ICK.ar_cisco_fmc` role waits for the FMC REST API and for FTDv to finish booting, starts a 90-day Smart License evaluation (required before FMCv will accept FTD), creates a lab access policy, then registers FTDv and waits until the device appears in FMC. FMC accepting registration (`202`) is not enough — first boot plus sftunnel join often takes another 10–30 minutes. Seeing FTD under **Devices** is registration success, not a successful policy deploy. The REST add-device API defaults the performance tier to **FTDv50** (12 vCPU / 24 GB); this lab uses `c5.xlarge` (4 vCPU / 8 GB), so the role registers **FTDv5**, names Ethernet0/0 `outside` (`10.0.4.x`) and Ethernet0/1 `inside` (`10.0.5.x`), and submits the first deploy. Use it from the `aws/cisco_fmc_ftd_aws` template. The AWS account must already be subscribed to the Cisco FMCv and FTDv Marketplace listings. **FMC/FTD logging to Splunk is not automated** — configure Audit Log and Integrations > Splunk in the FMC GUI after the build (see [Templates](templates.md#cisco_fmc_ftd_aws)).

## Splunk syslog inputs

The `aws/cisco_fmc_ftd_aws` template builds **Splunk first**, then FMC/FTD, then Windows on the FTD inside network:

1. `P4T12ICK.ludus_ar_splunk` — install Splunk Enterprise on `10.0.2.10` with **Cisco Security Cloud** in `ludus_ar_splunk_apps`, and with `ludus_ar_splunk_syslog: true` create index `syslog` plus UDP/TCP inputs on **514** (FMC audit, `cisco:fmc:audit`) and **1514** (FTD events, `cisco:ftd:syslog`).
2. `P4T12ICK.ar_cisco_fmc` — register FTD, name inside/outside interfaces, attach security zones, add an allow-and-log rule with lab IPS policy **AR-IPS-Policy** (Balanced base, Snort 3 SID `1:498` **INDICATOR-COMPROMISE id check returned root** enabled so `http://testmyids.com/` alerts), PAT `10.0.5.0/24` to the outside interface, and route VPN/mgmt/default via outside. Configure FMC Audit Log (`10.0.2.10:514`) and Integrations > Splunk (`10.0.2.10:1514`) in the GUI after the build.
3. `P4T12ICK.ludus_ar_windows` — Windows Server 2022 at `10.0.5.11` (`network: inside`). Traffic to Splunk and the internet is steered through FTDv (inside PAT to the outside interface).

Search in Splunk:

- Audit logs: `index=syslog sourcetype=cisco:fmc:audit`
- Firewall events: `index=syslog sourcetype=cisco:ftd:syslog`

## Summary

- **Templates** define which Ansible roles run on which servers via the **roles** list under each server in `attack_range`.
- **Any Ansible Galaxy role** can be used: list it by name (e.g. `namespace.role_name`). Attack Range installs it and runs it at build time.
- For **local role development**, set `ATTACK_RANGE_LOCAL_ROLES` to map Galaxy names to local paths (see above).
- Use **vars** (dict form) to pass variables to a role. Use **inventory_name** when the role expects a specific host group.
- To define a new configuration, create or edit a template, add the desired Galaxy roles (and vars), and build from that template. No code changes are required.

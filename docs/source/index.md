# Attack Range Documentation

The Splunk Attack Range builds instrumented cloud environments (AWS, Azure, GCP), simulates attacks, and forwards data into Splunk for detection development and testing.

The preferred way to run Attack Range is **Docker Compose**, which starts the web app and API (and optionally the CLI) without installing Python, Ansible, or Terraform locally.

```{toctree}
:caption: Contents
:maxdepth: 2

getting-started
configuration
networking
sharing
templates
ansible-roles
```

## Quick links

- **Getting Started** — Docker Compose, web app, API, and CLI.
- **Configuration** — Config file structure and provider options.
- **Networking** — Two-phase build and connectivity; includes a **WireGuard VPN** section (why WireGuard, server/client, config storage, official clients, sharing).
- **Sharing** — Giving others access with additional WireGuard configs.
- **Templates** — Built-in templates, including the Cisco lab and how to send FMC/FTD logs to Splunk.
- **Ansible Roles** — Bundled roles (Atomic Red Team, CAP Attack, data replay, PurpleSharp) and how they are used.

# Getting Started

This guide gets you running Attack Range using Docker Compose (recommended), then explains the web app, API, and CLI.

## Prerequisites

- **Docker** and **Docker Compose** installed.
- A cloud account and CLI configured for one of: **AWS**, **Azure**, or **GCP**.
- Credentials on the host so the containers can use them:
  - **AWS:** `~/.aws` (e.g. `aws configure`)
  - **Azure:** `~/.azure` (e.g. `az login`)
  - **GCP:** `~/.config/gcloud` (e.g. `gcloud auth login`)

## Running with Docker Compose (recommended)

Docker Compose runs the API, web app, and (optionally) the CLI without installing Python, Ansible, or Terraform on your machine.

1. **Start the stack:**

   ```bash
   git clone https://github.com/splunk/attack_range.git
   cd attack_range
   docker compose -f docker/docker-compose.yml build --no-cache
   docker compose -f docker/docker-compose.yml up
   ```

   This starts:

   - The **API** on port **4000**
   - The **Web app** on port **4321**

2. **Open the web app:** [http://localhost:4321](http://localhost:4321)

3. **Build your first range:**

   - Choose a template (e.g. **aws/splunk_minimal_aws**).
   - Click build. The backend runs **Phase 1** (VPN infrastructure).
   - When status changes to **Waiting for VPN**, download/copy the WireGuard client config.
   - Connect to the VPN using WireGuard (Desktop or mobile). If you are using WSL2 make sure to install WireGuard on the host machine not the WSL instance.
   - Click **Continue build** to run **Phase 2** (lab: Splunk, Windows, etc.).

4. **Optional — CLI in Docker:**

   ```bash
   docker compose --profile cli -f docker/docker-compose.yml run --rm attack_range build -t aws/splunk_minimal_aws
   ```

   The CLI will prompt you to connect to the VPN, then continue the lab build. Other commands: `destroy`, `simulate`, `share` (see [Configuration](configuration.md) and CLI sections below).

## Using the Web App

- **Build:** Select a template and start build; when status is *Waiting for VPN*, download the WireGuard config, connect, then continue.
- **List / status:** See all ranges and their status (building, running, error).
- **Destroy:** Tear down a range by its Attack Range ID.
- **Simulate:** Run Atomic Red Team techniques against a server in a running range (attack range ID, target server, technique list).
- **Share:** Generate a new WireGuard config for a named user; config is saved and shown for sharing.

The app talks to the API at `http://localhost:4000` (or `PUBLIC_API_URL` in Docker).

## Using the API

The REST API runs on port **4000** and provides:

- **Health:** `GET /health`
- **Build (two-phase):** `POST /attack-range/build` with `template` (phase 1) or `attack_range_id` (phase 2 after VPN).
- **Status:** `GET /attack-range/status/<attack_range_id>`
- **List:** `GET /attack-range/list`
- **Destroy:** `POST /attack-range/destroy` with `attack_range_id`
- **Simulate:** `POST /attack-range/simulate` with `attack_range_id`, `target`, `techniques`
- **Share:** `POST /attack-range/share` with `attack_range_id`, `name`
- **Templates:** `GET /templates`, `GET /templates/<provider>/<name>`
- **Configs:** `GET /configs`, `GET /configs/<config_id>`
- **Providers:** `GET /providers/check` (CLI/credentials availability)

Interactive API docs:

- **Swagger UI:** [http://localhost:4000/openapi/swagger](http://localhost:4000/openapi/swagger)
- **OpenAPI JSON:** [http://localhost:4000/openapi/openapi.json](http://localhost:4000/openapi/openapi.json)

All build/destroy operations are asynchronous: you get an `attack_range_id` and poll the status endpoint until the range is `running` or `error`.

## Using the CLI

You can run the CLI:

- **Inside Docker** (recommended):  
  `docker compose --profile cli -f docker/docker-compose.yml run --rm attack_range <action> [options]`
- **Locally:** from the project root, `python attack_range.py <action> [options]` (requires Python, Ansible, Terraform, and cloud CLI on the host).

### CLI actions

- **build** — Build from a template (two-phase: VPN then lab; CLI prompts for VPN connection).
  - `python attack_range.py build -t aws/splunk_minimal_aws`
  - Template can be `provider/name` or `name` (searched in `templates/`).

- **destroy** — Tear down a range.
  - `python attack_range.py destroy`
  - With a single config in `config/`, that config is used. Otherwise: `python attack_range.py destroy -c <config_path_or_id>`.

- **simulate** — Run Atomic Red Team techniques on a target server.
  - `python attack_range.py simulate -t <target_server_name> -te T1003.001,T1059.003 [-c config]`

- **share** — Generate a new WireGuard client config for sharing.
  - `python attack_range.py share -n alice [-c config]`

Config can be a path or an attack range ID (e.g. `uuid.yml` in `config/`). If omitted and there is exactly one `*.yml` in `config/`, it is used.

## Two-phase build (VPN then lab)

Attack Range uses a two-phase build so the lab is only reachable over VPN:

1. **Phase 1 (VPN):** Terraform creates the network and a router; Ansible configures WireGuard on the router and generates a client config. Status becomes `wait_for_vpn`.
2. **You:** Download or copy the WireGuard config, connect with the WireGuard client.
3. **Phase 2 (Lab):** You trigger the continuation (in the app or with a second API call or by answering the CLI prompt). Ansible provisions Splunk, Windows, Kali, etc. over the VPN. Status becomes `running`.

This keeps lab IPs (e.g. 10.0.2.x) off the public internet.

## Next steps

- [Configuration](configuration.md) — Config file layout, providers, and options.
- [Networking](networking.md) — WireGuard, VPN, and connectivity.
- [Sharing](sharing.md) — Sharing access with others.
- [Templates](templates.md) — Available templates and structure.
- [Ansible Roles](ansible-roles.md) — Roles used for install and simulation.

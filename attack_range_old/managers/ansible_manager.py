"""
Ansible manager for Attack Range.

This module handles Ansible operations including inventory management,
playbook updates, and playbook execution.
"""

import base64
import io
import json
import os
import sys
import re
import shutil
import tarfile
import tempfile
import yaml
import time
import socket
import subprocess
import shlex
import logging
import ansible_runner
from typing import Optional, Dict, Any, List

from attack_range.utils import server_private_ip

# Galaxy role that must always be updated to latest before VPN playbooks (vpn.yaml, vpn_config.yaml)
WIREGUARD_GALAXY_ROLE = "p4t12ick.ar_wireguard_vpn"
WG_CI_CLIENT_CONFIG = "client1.conf"
WG_CI_ROUTER_IP = "10.0.1.10"
LOCAL_ROLE_MAX_TAR_BYTES = 50 * 1024 * 1024
APPLY_LOCAL_ROLES_PLAYBOOK = "apply_local_roles.yaml"


def resolve_local_role_name(role_path: str, override: Optional[str] = None) -> str:
    """Resolve Galaxy-style role name from meta/main.yml or directory basename."""
    if override and str(override).strip():
        return str(override).strip()

    meta_candidates = (
        os.path.join(role_path, "meta", "main.yml"),
        os.path.join(role_path, "meta", "main.yaml"),
    )
    meta_file = next((path for path in meta_candidates if os.path.isfile(path)), None)
    if meta_file:
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        galaxy_info = meta.get("galaxy_info") or {}
        role_name = galaxy_info.get("role_name")
        namespace = galaxy_info.get("namespace") or galaxy_info.get("author")
        if role_name and namespace:
            return f"{namespace}.{role_name}"
        if role_name:
            return str(role_name)

    return os.path.basename(os.path.abspath(role_path))

_ART_SUMMARY_TASK_MARKERS = (
    "Atomic Red Team execution summary",
    "Simulate playbook execution status",
)
_ART_RUN_TASK_MARKERS = (
    "Run specified Atomic Red Team Technique",
    "Execute Atomic Red Team test",
)


def _normalize_art_execution_result(entry: dict) -> dict:
    """Normalize one atomic execution record from Ansible facts or events."""
    technique = entry.get("technique", "unknown")
    if isinstance(technique, dict):
        technique = technique.get("technique", "unknown")
    guid = str(entry.get("guid") or "").strip()
    success = bool(entry.get("success"))
    return {
        "technique": str(technique),
        "guid": guid,
        "success": success,
        "failed": bool(entry.get("failed", not success)),
        "return_code": int(entry.get("return_code", entry.get("rc", -1))),
        "stdout_lines": list(entry.get("stdout_lines") or []),
        "stderr_lines": list(entry.get("stderr_lines") or []),
        "stdout": str(entry.get("stdout") or ""),
        "stderr": str(entry.get("stderr") or ""),
        "error": str(entry.get("error") or entry.get("msg") or ""),
    }


def _parse_debug_msg_payload(msg: Any) -> dict | None:
    """Parse structured data from an Ansible debug task ``msg`` field."""
    if isinstance(msg, dict):
        if "results" in msg or "summary" in msg:
            return msg
        return None
    if isinstance(msg, str) and msg.strip():
        try:
            parsed = json.loads(msg)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _technique_from_task_vars(task_vars: dict) -> tuple[str, str]:
    item = task_vars.get("item")
    if isinstance(item, dict):
        technique = str(item.get("technique") or "unknown")
        guid = str(item.get("guid") or "").strip()
        return technique, guid
    technique = str(task_vars.get("technique") or item or "unknown")
    guid = str(task_vars.get("atomic_test_guid") or task_vars.get("guid") or "").strip()
    return technique, guid


def _extract_atomic_simulation_output(
    events_list: list,
    extra_vars: dict | None = None,
) -> dict:
    """
    Build structured atomic execution output from Ansible runner events.

    Returns a dict with ``results``, ``summary``, and ``by_host`` keys.
    """
    by_host: dict[str, dict] = {}
    extra_vars = extra_vars or {}

    for event in events_list:
        event_data = event.get("event_data", {})
        event_type = event.get("event", "")
        if event_type not in ("runner_on_ok", "runner_on_failed"):
            continue

        task_name = str(event_data.get("task") or "")
        host = str(event_data.get("host") or "unknown")
        res = event_data.get("res", {}) or {}

        if any(marker in task_name for marker in _ART_SUMMARY_TASK_MARKERS):
            payload = _parse_debug_msg_payload(res.get("msg"))
            if not payload and "results" in res:
                payload = res
            if not payload:
                continue
            results = payload.get("results") or []
            summary = payload.get("summary") or {}
            status = payload.get("status")
            if not status and summary:
                failed = int(summary.get("failed", 0) or 0)
                status = "failed" if failed else "success"
            normalized = [_normalize_art_execution_result(r) for r in results if isinstance(r, dict)]
            by_host[host] = {
                "results": normalized,
                "summary": summary,
                "status": status or "unknown",
            }
            continue

        if any(marker in task_name for marker in _ART_RUN_TASK_MARKERS):
            task_vars = event_data.get("task_vars", {}) or {}
            technique, guid = _technique_from_task_vars(task_vars)
            stdout_lines = res.get("stdout_lines") or []
            stderr_lines = res.get("stderr_lines") or []
            if not stdout_lines and res.get("stdout"):
                stdout_lines = str(res.get("stdout")).splitlines()
            if not stderr_lines and res.get("stderr"):
                stderr_lines = str(res.get("stderr")).splitlines()
            failed = bool(res.get("failed"))
            rc = int(res.get("rc", 1 if failed else 0))
            entry = _normalize_art_execution_result(
                {
                    "technique": technique,
                    "guid": guid,
                    "success": not failed and rc == 0,
                    "failed": failed,
                    "return_code": rc,
                    "stdout_lines": stdout_lines,
                    "stderr_lines": stderr_lines,
                    "stdout": res.get("stdout", ""),
                    "stderr": res.get("stderr", ""),
                    "error": res.get("msg", ""),
                }
            )
            host_bucket = by_host.setdefault(
                host,
                {"results": [], "summary": {}, "status": "unknown"},
            )
            host_bucket["results"].append(entry)

    # Recompute per-host summaries when built from individual run tasks.
    for host, payload in by_host.items():
        results = payload.get("results") or []
        if results and not payload.get("summary"):
            succeeded = sum(1 for r in results if r.get("success"))
            failed = len(results) - succeeded
            payload["summary"] = {
                "total": len(results),
                "succeeded": succeeded,
                "failed": failed,
            }
            payload["status"] = "failed" if failed else "success"

    all_results: list[dict] = []
    for payload in by_host.values():
        all_results.extend(payload.get("results") or [])

    total = len(all_results)
    succeeded = sum(1 for r in all_results if r.get("success"))
    failed = total - succeeded
    merged_summary = {
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
    }
    overall_status = "unknown"
    if total:
        overall_status = "failed" if failed else "success"
    elif extra_vars.get("techniques") or extra_vars.get("atomics") or extra_vars.get("atomic_files"):
        overall_status = "unknown"

    if not all_results and not by_host:
        return {}

    return {
        "status": overall_status,
        "summary": merged_summary,
        "results": all_results,
        "by_host": by_host,
    }


class AnsibleManager:
    """Manages Ansible operations."""

    def __init__(self, ansible_dir: str, inventory_path: str, config: dict, cloud_provider: str, logger: logging.Logger):
        """
        Initialize the Ansible manager.

        :param ansible_dir: Directory containing Ansible configuration
        :param inventory_path: Path to inventory.yaml file
        :param config: Configuration dictionary
        :param cloud_provider: Cloud provider (aws, azure, gcp)
        :param logger: Logger instance
        """
        self.ansible_dir = ansible_dir
        self.inventory_path = inventory_path
        self.config = config
        self.cloud_provider = cloud_provider
        self.logger = logger

    def _load_inventory(self) -> dict:
        """Load inventory from file, or return minimal structure if file does not exist (fully auto-generated)."""
        if os.path.isfile(self.inventory_path):
            with open(self.inventory_path, 'r') as f:
                return yaml.safe_load(f)
        return {'vpn': {'hosts': {}}}

    def update_inventory(self, router_public_ip: str) -> None:
        """
        Create or update the inventory.yaml file with the router public IP and SSH key path.
        The file is generated from scratch if it does not exist.

        :param router_public_ip: Public IP address of the router
        """
        self.logger.info(f"Updating inventory with router public IP: {router_public_ip}")

        inventory = self._load_inventory()

        # Get SSH private key path from config
        if self.cloud_provider == "azure":
            private_key_path = os.path.expanduser(self.config.get("azure", {}).get("private_key_path", "~/.ssh/id_rsa"))
        elif self.cloud_provider == "gcp":
            private_key_path = os.path.expanduser(self.config.get("gcp", {}).get("private_key_path", "~/.ssh/id_rsa"))
        else:  # aws
            private_key_path = os.path.expanduser(self.config.get("aws", {}).get("private_key_path", "~/.ssh/id_rsa"))

        # Update the vpn host IP and SSH key path
        if 'vpn' not in inventory:
            inventory['vpn'] = {'hosts': {}}
        if 'hosts' not in inventory['vpn']:
            inventory['vpn']['hosts'] = {}

        # Remove old IP key if it exists and is different
        old_ips = list(inventory['vpn']['hosts'].keys())
        for old_ip in old_ips:
            if old_ip != router_public_ip:
                # Copy the config from old IP if it exists
                host_config = inventory['vpn']['hosts'].get(old_ip, {})
                # Remove old IP
                del inventory['vpn']['hosts'][old_ip]
                # Add new IP with config (will update SSH key below)
                if router_public_ip not in inventory['vpn']['hosts']:
                    inventory['vpn']['hosts'][router_public_ip] = host_config
                break

        # Ensure VPN host entry exists with default config if needed
        if router_public_ip not in inventory['vpn']['hosts']:
            inventory['vpn']['hosts'][router_public_ip] = {
                'ansible_user': 'ubuntu'  # Router always uses ubuntu
            }

        # Update SSH key path for VPN host
        inventory['vpn']['hosts'][router_public_ip]['ansible_ssh_private_key_file'] = private_key_path

        # Write updated inventory
        with open(self.inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False, sort_keys=False)

        self.logger.info(f"Inventory updated successfully with SSH key: {private_key_path}")

    def update_inventory_attack_range_servers(self) -> None:
        """
        Create or update the inventory.yaml file with attack_range servers from config.
        Generates inventory entries dynamically based on attack_range configuration.
        Uses inventory_name from roles when specified, otherwise uses the entry's name.
        The file is generated from scratch if it does not exist.
        """
        self.logger.info("Updating inventory with attack_range servers from config...")

        inventory = self._load_inventory()

        # Get attack_range configuration
        attack_range_config = self.config.get("attack_range", [])

        # Get private key path from config
        if self.cloud_provider == "azure":
            private_key_path = os.path.expanduser(self.config.get("azure", {}).get("private_key_path", "~/.ssh/id_rsa"))
        elif self.cloud_provider == "gcp":
            private_key_path = os.path.expanduser(self.config.get("gcp", {}).get("private_key_path", "~/.ssh/id_rsa"))
        else:  # aws
            private_key_path = os.path.expanduser(self.config.get("aws", {}).get("private_key_path", "~/.ssh/id_rsa"))

        # Remove old attack_range server entries (keep vpn)
        keys_to_remove = [key for key in inventory.keys() if key != 'vpn']
        for key in keys_to_remove:
            del inventory[key]

        # Add attack_range servers dynamically
        for server in attack_range_config:
            server_name = server.get("name")
            ip_last_octet = server.get("ip_last_octet")
            is_windows = server.get("windows", False)
            is_linux = server.get("linux", False)
            is_cisco_fmc = bool(server.get("cisco_fmc"))
            is_cisco_ftd = bool(server.get("cisco_ftd"))
            roles = server.get("roles", [])

            if not server_name or ip_last_octet is None:
                self.logger.warning(f"Skipping server entry missing name or ip_last_octet: {server}")
                continue

            private_ip = server_private_ip(server)

            # Build host configuration
            host_config = {}

            if is_cisco_fmc or is_cisco_ftd:
                # Appliances have no Python/SSH for Ansible; FMC is configured via REST from the controller.
                host_config = {
                    "ansible_connection": "local",
                    "ansible_python_interpreter": sys.executable,
                    "ansible_user": server.get("user_name", "admin"),
                    "ansible_password": self.config["general"]["attack_range_password"],
                }
            elif is_windows:
                # Windows configuration
                # Use user_name from config if provided, otherwise default based on cloud provider
                windows_user = server.get("user_name")
                if not windows_user:
                    windows_user = "AzureAdmin" if self.cloud_provider == "azure" else "Administrator"
                host_config = {
                    "ansible_user": windows_user,
                    "ansible_password": self.config["general"]["attack_range_password"],
                    "ansible_connection": "winrm",
                    "ansible_winrm_server_cert_validation": "ignore",
                    "ansible_port": 5985,
                    "ansible_winrm_operation_timeout_sec": 600,
                    "ansible_winrm_read_timeout_sec": 1200,
                    "ansible_winrm_connection_timeout": 600,
                    "ansible_winrm_transport": "basic",
                    "ansible_winrm_scheme": "http",
                    "ansible_winrm_kerberos_delegation": False,
                    "ansible_winrm_message_encryption": "never",
                    "ansible_winrm_retry_timeout": 3600,
                    "ansible_winrm_retry_interval": 15,
                    "ansible_winrm_connection_retries": 40,
                }
            elif is_linux:
                # Linux configuration
                # Use user_name from config if provided, otherwise default to ubuntu
                linux_user = server.get("user_name", "ubuntu")
                host_config = {
                    "ansible_user": linux_user,
                    "ansible_ssh_private_key_file": private_key_path,
                }
                # Set Python interpreter - can be overridden in config
                # RHEL 8 uses /usr/libexec/platform-python, others typically use /usr/bin/python3
                python_interpreter = server.get("ansible_python_interpreter")
                if python_interpreter:
                    host_config["ansible_python_interpreter"] = python_interpreter
                else:
                    # Auto-detect RHEL from AMI filter and use platform-python
                    ami_filter = server.get("ami_name_filter", "")
                    if "RHEL" in ami_filter.upper():
                        # RHEL 8 uses platform-python
                        host_config["ansible_python_interpreter"] = "/usr/libexec/platform-python"
                    else:
                        # Default: use python3 (common on most Linux distributions)
                        host_config["ansible_python_interpreter"] = "/usr/bin/python3"
            else:
                # Default to Linux if not specified
                linux_user = server.get("user_name", "ubuntu")
                host_config = {
                    "ansible_user": linux_user,
                    "ansible_ssh_private_key_file": private_key_path,
                }
                # Set Python interpreter for default Linux hosts
                python_interpreter = server.get("ansible_python_interpreter")
                if python_interpreter:
                    host_config["ansible_python_interpreter"] = python_interpreter
                else:
                    # Auto-detect RHEL from AMI filter and use platform-python
                    ami_filter = server.get("ami_name_filter", "")
                    if "RHEL" in ami_filter.upper():
                        # RHEL 8 uses platform-python
                        host_config["ansible_python_interpreter"] = "/usr/libexec/platform-python"
                    else:
                        # Default: use python3 (common on most Linux distributions)
                        host_config["ansible_python_interpreter"] = "/usr/bin/python3"

            # Determine inventory group names from roles
            inventory_groups = set()

            if roles:
                # Use inventory_name from roles if specified, otherwise use server_name
                for role in roles:
                    if isinstance(role, dict):
                        inventory_name = role.get("inventory_name")
                        if inventory_name:
                            inventory_groups.add(inventory_name)
                        else:
                            inventory_groups.add(server_name)
                    else:
                        # If role is just a string, use server_name
                        inventory_groups.add(server_name)
            else:
                # No roles specified, use server_name
                inventory_groups.add(server_name)

            # Add host to each inventory group
            for group_name in inventory_groups:
                if group_name not in inventory:
                    inventory[group_name] = {"hosts": {}}

                inventory[group_name]["hosts"][private_ip] = host_config

        # Write updated inventory
        with open(self.inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self.logger.info(f"Inventory updated successfully with {len(attack_range_config)} server(s)")

    def update_inventory_password(self) -> None:
        """
        Update the ansible_password in the inventory.yaml file for Windows hosts.
        Handles both inventory_name and name-based inventory groups.
        """
        self.logger.info("Updating ansible_password in inventory...")

        inventory = self._load_inventory()

        # Update the ansible_password for all Windows hosts
        attack_range_config = self.config.get("attack_range", [])
        password = self.config["general"]["attack_range_password"]

        for server in attack_range_config:
            server_name = server.get("name")
            is_windows = server.get("windows", False)
            roles = server.get("roles", [])

            if not is_windows:
                continue

            # Determine which inventory groups contain this server
            inventory_groups = set()

            if roles:
                # Use inventory_name from roles if specified, otherwise use server_name
                for role in roles:
                    if isinstance(role, dict):
                        inventory_name = role.get("inventory_name")
                        if inventory_name:
                            inventory_groups.add(inventory_name)
                        else:
                            inventory_groups.add(server_name)
                    else:
                        inventory_groups.add(server_name)
            else:
                inventory_groups.add(server_name)

            # Update password for all relevant inventory groups
            for group_name in inventory_groups:
                if group_name in inventory and 'hosts' in inventory[group_name]:
                    win_hosts = inventory[group_name]['hosts']
                    for host_ip in win_hosts:
                        if 'ansible_password' in win_hosts[host_ip]:
                            win_hosts[host_ip]['ansible_password'] = password

        # Write updated inventory
        with open(self.inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False, sort_keys=False)

        self.logger.info("Inventory password updated successfully")

    def _vpn_allowed_ips(self) -> str:
        """Return WireGuard AllowedIPs for lab subnets, including Cisco FTD data nets when present."""
        cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
        if any(server.get("cisco_ftd") for server in self.config.get("attack_range", [])):
            cidrs.extend(["10.0.3.0/24", "10.0.4.0/24", "10.0.5.0/24"])
        return ", ".join(cidrs)

    def _get_vpn_clients(self) -> list:
        """Return vpn_clients from config or default for playbook generation."""
        return self.config.get("general", {}).get("vpn_clients") or [
            {"name": "client1", "address": "10.0.1.11/32"}
        ]

    def _get_vpn_physical_interface(self) -> str:
        """Return physical interface name for the current cloud provider."""
        if self.cloud_provider == "azure":
            return "eth0"
        if self.cloud_provider == "gcp":
            return "ens4"
        return "ens5"  # aws

    def update_vpn_playbook(self, router_public_ip: str) -> None:
        """
        Generate the vpn.yaml playbook from scratch (deploy WireGuard server).
        Uses router public IP, cloud-specific interface, and vpn_clients from config.
        """
        vpn_playbook_path = os.path.join(self.ansible_dir, "vpn.yaml")
        self.logger.info(f"Generating vpn.yaml with router public IP: {router_public_ip}")

        physical_interface = self._get_vpn_physical_interface()
        vpn_clients = self._get_vpn_clients()

        play = {
            "hosts": "vpn",
            "become": True,
            "roles": [
                {
                    "role": "p4t12ick.ar_wireguard_vpn",
                    "vpn_physical_interface": physical_interface,
                    "vpn_address": "10.0.1.10/24",
                    "vpn_allowed_ips": self._vpn_allowed_ips(),
                    "vpn_endpoint": router_public_ip,
                    "wireguard_action": "deploy",
                    "vpn_clients": vpn_clients,
                }
            ],
        }

        with open(vpn_playbook_path, "w") as f:
            yaml.dump([play], f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self.logger.info(f"vpn.yaml generated successfully (interface: {physical_interface})")

    def update_vpn_config_playbook(self) -> None:
        """
        Generate the vpn_config.yaml playbook from scratch (get WireGuard client config).
        Uses vpn_clients from config.
        """
        vpn_config_playbook_path = os.path.join(self.ansible_dir, "vpn_config.yaml")
        self.logger.info("Generating vpn_config.yaml...")

        vpn_clients = self._get_vpn_clients()

        play = {
            "hosts": "vpn",
            "become": True,
            "roles": [
                {
                    "role": "p4t12ick.ar_wireguard_vpn",
                    "wireguard_action": "get_config",
                    "vpn_allowed_ips": self._vpn_allowed_ips(),
                    "vpn_clients": vpn_clients,
                }
            ],
        }

        with open(vpn_config_playbook_path, "w") as f:
            yaml.dump([play], f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self.logger.info("vpn_config.yaml generated successfully")

    def update_lab_playbook(self) -> None:
        """
        Update the lab.yaml playbook based on the attack_range configuration.
        Generates the playbook dynamically from the config.yml attack_range section.
        Uses inventory_name from roles when specified, otherwise uses the entry's name.
        Groups multiple roles with the same hosts into a single play.
        """
        lab_playbook_path = os.path.join(self.ansible_dir, "lab.yaml")

        self.logger.info("Updating lab.yaml playbook from config...")

        # Get attack_range configuration
        attack_range_config = self.config.get("attack_range", [])

        if not attack_range_config:
            self.logger.warning("No attack_range configuration found in config.yml")
            return

        # Build the playbook structure
        # Use a dictionary to group roles by hosts name
        plays_by_hosts = {}

        for entry in attack_range_config:
            if entry.get("cisco_ftd"):
                # FTD is configured by day-0 user-data and FMC registration, not SSH Ansible.
                continue

            entry_name = entry.get("name")
            roles = entry.get("roles", [])

            if not roles:
                # No roles specified, create a play with entry name
                hosts_name = entry_name
                if hosts_name not in plays_by_hosts:
                    plays_by_hosts[hosts_name] = {
                        "hosts": hosts_name,
                        "roles": []
                    }

                # Add vars section if role_vars exist
                role_vars = entry.get("role_vars", {})
                if role_vars:
                    plays_by_hosts[hosts_name]["vars"] = role_vars
            else:
                # Process each role and group by hosts name
                for role in roles:
                    # Determine hosts name: use inventory_name if specified, otherwise use entry_name
                    if isinstance(role, dict):
                        inventory_name = role.get("inventory_name")
                        hosts_name = inventory_name if inventory_name else entry_name
                        role_name = role.get("role")

                        if not role_name:
                            self.logger.warning(f"Skipping role entry missing 'role' field: {role}")
                            continue

                        # Create role dict for Ansible (role name + vars if present)
                        role_dict = {"role": role_name}
                        role_vars = role.get("vars")
                        if role_vars:
                            role_dict["vars"] = role_vars

                        # Initialize play for this hosts group if it doesn't exist
                        if hosts_name not in plays_by_hosts:
                            plays_by_hosts[hosts_name] = {
                                "hosts": hosts_name,
                                "roles": []
                            }

                        # Add role to the play
                        plays_by_hosts[hosts_name]["roles"].append(role_dict)
                    else:
                        # Role is just a string, use entry_name as hosts
                        hosts_name = entry_name
                        if hosts_name not in plays_by_hosts:
                            plays_by_hosts[hosts_name] = {
                                "hosts": hosts_name,
                                "roles": []
                            }

                        plays_by_hosts[hosts_name]["roles"].append(role)

        # Convert dictionary to list of plays
        plays = []
        for hosts_name, play_data in plays_by_hosts.items():
            play = {
                "hosts": play_data["hosts"],
                "roles": play_data["roles"]
            }
            # Check if this is a Windows host - don't set become: true for Windows
            is_windows = False
            is_cisco_fmc = False
            entry_become = None
            for entry in attack_range_config:
                entry_name = entry.get("name")
                roles = entry.get("roles", [])
                # Check if this entry matches the hosts_name
                if entry_name == hosts_name:
                    is_windows = entry.get("windows", False)
                    is_cisco_fmc = bool(entry.get("cisco_fmc"))
                    entry_become = entry.get("become")
                    break
                # Check if any role in this entry has inventory_name matching hosts_name
                for role in roles:
                    if isinstance(role, dict) and role.get("inventory_name") == hosts_name:
                        is_windows = entry.get("windows", False)
                        is_cisco_fmc = bool(entry.get("cisco_fmc"))
                        entry_become = entry.get("become")
                        break
                if entry_become is not None or is_windows or is_cisco_fmc:
                    break

            # Don't set become: true for Windows hosts, otherwise default to become: true
            if is_cisco_fmc:
                play["connection"] = "local"
                play["gather_facts"] = False
                play["become"] = False if entry_become is None else entry_become
            elif is_windows:
                play["gather_facts"] = True
                play["pre_tasks"] = [
                    {
                        "name": "Wait for WinRM",
                        "ansible.builtin.wait_for": {
                            "host": "{{ inventory_hostname }}",
                            "port": 5985,
                            "timeout": 3600,
                            "sleep": 10,
                            "msg": "WinRM on {{ inventory_hostname }}:5985 did not become reachable",
                        },
                        "delegate_to": "localhost",
                        "vars": {
                            "ansible_connection": "local",
                            "ansible_python_interpreter": "{{ ansible_playbook_python }}",
                        },
                    }
                ]
                # Windows hosts don't use become: true at playbook level
                if entry_become is not None:
                    play["become"] = entry_become
                # Otherwise, don't add become at all for Windows
            elif entry_become is not None:
                play["become"] = entry_become
            else:
                play["become"] = True

            # Add vars if they exist
            if "vars" in play_data:
                play["vars"] = play_data["vars"]
            plays.append(play)

        # Write the playbook
        with open(lab_playbook_path, 'w') as f:
            yaml.dump(plays, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self.logger.info(f"lab.yaml updated successfully with {len(plays)} play(s)")

    def wait_for_ssh(self, host: str, port: int = 22, timeout: int = 300, check_interval: int = 5) -> bool:
        """
        Wait for SSH to become available on a host.

        :param host: Host IP address or hostname
        :param port: SSH port (default 22)
        :param timeout: Maximum time to wait in seconds (default 300 = 5 minutes)
        :param check_interval: Time between checks in seconds (default 5)
        :return: True if SSH becomes available, False if timeout
        """
        self.logger.info(f"Waiting for SSH to become available on {host}:{port} (timeout: {timeout}s)...")

        start_time = time.time()
        attempt = 0

        while time.time() - start_time < timeout:
            attempt += 1
            try:
                # Try to establish a TCP connection to the SSH port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    self.logger.info(f"SSH is available on {host}:{port} (took {int(time.time() - start_time)}s, {attempt} attempts)")
                    # Give it a few more seconds for SSH to fully initialize
                    time.sleep(10)
                    return True

            except (socket.error, socket.timeout) as e:
                pass

            if attempt % 6 == 0:  # Log every 30 seconds (6 * 5s interval)
                elapsed = int(time.time() - start_time)
                self.logger.info(f"Still waiting for SSH on {host}... ({elapsed}s elapsed)")

            time.sleep(check_interval)

        self.logger.error(f"Timeout waiting for SSH on {host}:{port} after {timeout}s")
        return False

    @staticmethod
    def _strip_dns_from_wireguard_config_content(content: str) -> str:
        """Remove DNS= lines so wg-quick does not break public DNS on CI runners."""
        lines = [
            line
            for line in content.splitlines()
            if not re.match(r"^\s*DNS\s*=", line, re.IGNORECASE)
        ]
        return "\n".join(lines) + ("\n" if lines else "")

    def _prepare_ci_wireguard_config(self) -> str:
        """
        Return a WireGuard client config path suitable for CI (no DNS override).

        wg-quick applies DNS= from the client config via resolvconf/systemd-resolved,
        which breaks outbound DNS on GitHub Actions even with split-tunnel AllowedIPs.
        Strips DNS from client1.conf in place and restores the original on disconnect.
        """
        source_path = self._ci_wireguard_config_path()
        with open(source_path, "r", encoding="utf-8") as f:
            original = f.read()
        stripped = self._strip_dns_from_wireguard_config_content(original)
        if stripped != original:
            self._ci_wireguard_config_original = original
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(stripped)
            self.logger.debug("CI mode: removed DNS override from WireGuard client config")
        return source_path

    def ensure_playbook_roles_installed(self, playbook_name: str, raise_on_failure: bool = False) -> None:
        """
        Install Ansible Galaxy roles required by a playbook.

        :param playbook_name: Playbook file name under the ansible directory
        :param raise_on_failure: If True, raise RuntimeError instead of sys.exit
        """
        playbook_path = os.path.join(self.ansible_dir, playbook_name)

        if not os.path.exists(playbook_path):
            error_msg = f"Playbook not found: {playbook_path}"
            if raise_on_failure:
                raise RuntimeError(error_msg)
            self.logger.error(error_msg)
            sys.exit(1)

        required_roles = self._get_required_roles_for_playbook(playbook_path)
        for role_name in required_roles:
            is_wireguard = role_name == WIREGUARD_GALAXY_ROLE
            if is_wireguard:
                if self._is_role_installed(role_name):
                    continue
                self.logger.info(f"Installing WireGuard role '{role_name}' from Ansible Galaxy...")
            elif not self._is_role_installed(role_name):
                self.logger.info(f"Installing required role '{role_name}' for playbook '{playbook_name}'")
            else:
                continue
            if not self.install_ansible_galaxy_role(role_name, force=not is_wireguard):
                error_msg = f"Failed to install required role '{role_name}' for playbook '{playbook_name}'"
                if raise_on_failure:
                    raise RuntimeError(error_msg)
                self.logger.error(error_msg)
                sys.exit(1)

        if WIREGUARD_GALAXY_ROLE in required_roles:
            self._patch_wireguard_allowed_ips()
            self._patch_wireguard_server_config()

    def run_ansible_playbook(self, playbook_name: str, extra_vars: dict = None) -> None:
        """
        Run an ansible playbook using ansible_runner.

        :param playbook_name: Name of the playbook file to run
        :param extra_vars: Optional dictionary of extra variables to pass to the playbook
        """
        playbook_path = os.path.join(self.ansible_dir, playbook_name)

        if not os.path.exists(playbook_path):
            self.logger.error(f"Playbook not found: {playbook_path}")
            sys.exit(1)

        self.ensure_playbook_roles_installed(playbook_name)

        self.logger.info(f"Running ansible playbook: {playbook_name}")

        # Run ansible playbook with inventory file
        cmdline = f"-i {self.inventory_path}"
        extra_vars_path = None

        # Add extra variables: use -e @file when any value is dict/list so Ansible gets correct types
        if extra_vars:
            if any(isinstance(v, (dict, list)) for v in extra_vars.values()):
                fd, extra_vars_path = tempfile.mkstemp(suffix=".yml")
                try:
                    with os.fdopen(fd, "w") as f:
                        yaml.dump(extra_vars, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
                    cmdline = f"{cmdline} -e @{extra_vars_path}"
                except Exception:
                    if extra_vars_path and os.path.exists(extra_vars_path):
                        try:
                            os.unlink(extra_vars_path)
                        except OSError:
                            pass
                    raise
            else:
                extra_vars_parts = [f"-e {k}={shlex.quote(str(v))}" for k, v in extra_vars.items()]
                cmdline = f"{cmdline} {' '.join(extra_vars_parts)}"

        runner = ansible_runner.run(
            private_data_dir=self.ansible_dir,
            cmdline=cmdline,
            playbook=playbook_name,
            verbosity=2,  # Increased verbosity for better error diagnostics
        )

        if extra_vars_path and os.path.exists(extra_vars_path):
            try:
                os.unlink(extra_vars_path)
            except OSError:
                pass

        if runner.status == "successful":
            self.logger.info(f"Playbook {playbook_name} completed successfully")
        else:
            self.logger.error(f"Playbook {playbook_name} failed with status: {runner.status}")
            
            # Log detailed error information
            if hasattr(runner, 'stats') and runner.stats:
                failures = runner.stats.get('failures', {})
                if failures:
                    self.logger.error(f"Failed hosts: {failures}")
                dark = runner.stats.get('dark', {})
                if dark:
                    self.logger.error(f"Unreachable hosts: {dark}")
            
            # Log events for debugging
            if hasattr(runner, 'events'):
                error_events = []
                for event in runner.events:
                    event_data = event.get('event_data', {})
                    if event.get('event') in ['runner_on_failed', 'runner_on_unreachable', 'runner_on_error']:
                        host = event_data.get('host', 'unknown')
                        task = event_data.get('task', 'unknown')
                        msg = event_data.get('msg', 'No error message')
                        error_events.append(f"Host: {host}, Task: {task}, Error: {msg}")
                
                if error_events:
                    self.logger.error("Ansible playbook errors:")
                    for error in error_events[-10:]:  # Show last 10 errors
                        self.logger.error(f"  - {error}")
            
            # Try to read stdout/stderr from the runner's artifact directory
            try:
                stdout_path = os.path.join(self.ansible_dir, 'artifacts', str(runner.config.ident), 'stdout')
                if os.path.exists(stdout_path):
                    with open(stdout_path, 'r') as f:
                        stdout_content = f.read()
                        if stdout_content:
                            # Log last 50 lines of stdout
                            lines = stdout_content.strip().split('\n')
                            self.logger.error("Last 50 lines of Ansible output:")
                            for line in lines[-50:]:
                                self.logger.error(f"  {line}")
            except Exception as e:
                self.logger.debug(f"Could not read stdout: {e}")
            
            sys.exit(1)

    def run_ansible_playbook_safe(self, playbook_name: str, extra_vars: dict = None) -> dict:
        """
        Run an ansible playbook using ansible_runner, raising exceptions instead of calling sys.exit.
        This is a safe version for use in API contexts where sys.exit would terminate the process.
        
        :param playbook_name: Name of the playbook file to run
        :param extra_vars: Optional dictionary of extra variables to pass to the playbook
        :return: Dictionary with execution output (host -> list of technique outputs) or None
        :raises RuntimeError: If playbook execution fails
        """
        playbook_path = os.path.join(self.ansible_dir, playbook_name)

        if not os.path.exists(playbook_path):
            error_msg = f"Playbook not found: {playbook_path}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        self.ensure_playbook_roles_installed(playbook_name, raise_on_failure=True)

        self.logger.info(f"Running ansible playbook: {playbook_name}")

        # Run ansible playbook with inventory file
        cmdline = f"-i {self.inventory_path}"
        extra_vars_path = None

        # Add extra variables: use -e @file when any value is dict/list so Ansible gets correct types
        if extra_vars:
            if any(isinstance(v, (dict, list)) for v in extra_vars.values()):
                fd, extra_vars_path = tempfile.mkstemp(suffix=".yml")
                try:
                    with os.fdopen(fd, "w") as f:
                        yaml.dump(extra_vars, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
                    cmdline = f"{cmdline} -e @{extra_vars_path}"
                except Exception:
                    if extra_vars_path and os.path.exists(extra_vars_path):
                        try:
                            os.unlink(extra_vars_path)
                        except OSError:
                            pass
                    raise
            else:
                extra_vars_parts = [f"-e {k}={shlex.quote(str(v))}" for k, v in extra_vars.items()]
                cmdline = f"{cmdline} {' '.join(extra_vars_parts)}"

        runner = ansible_runner.run(
            private_data_dir=self.ansible_dir,
            cmdline=cmdline,
            playbook=playbook_name,
            verbosity=2,  # Increased verbosity for better error diagnostics
        )

        if extra_vars_path and os.path.exists(extra_vars_path):
            try:
                os.unlink(extra_vars_path)
            except OSError:
                pass

        execution_output: dict = {}
        events_list: list = []

        if hasattr(runner, "events") and runner.events:
            try:
                events_list = list(runner.events)
                self.logger.debug(f"Processing {len(events_list)} Ansible events")
            except (TypeError, AttributeError):
                events_list = runner.events if isinstance(runner.events, list) else []

        if events_list:
            execution_output = _extract_atomic_simulation_output(events_list, extra_vars)

        if not execution_output and hasattr(runner, "config"):
            try:
                artifact_dir = os.path.join(self.ansible_dir, "artifacts", str(runner.config.ident))
                job_events_dir = os.path.join(artifact_dir, "job_events")
                if os.path.isdir(job_events_dir):
                    artifact_events = []
                    for event_file in sorted(os.listdir(job_events_dir)):
                        event_path = os.path.join(job_events_dir, event_file)
                        try:
                            with open(event_path, "r") as f:
                                artifact_events.append(json.load(f))
                        except (json.JSONDecodeError, OSError):
                            continue
                    execution_output = _extract_atomic_simulation_output(artifact_events, extra_vars)
            except Exception as e:
                self.logger.debug(f"Could not read simulation output from artifact files: {e}")

        if execution_output:
            summary = execution_output.get("summary", {})
            self.logger.info(
                "Extracted atomic execution output: "
                f"status={execution_output.get('status')} "
                f"total={summary.get('total')} "
                f"succeeded={summary.get('succeeded')} "
                f"failed={summary.get('failed')}"
            )
        else:
            self.logger.warning("No structured atomic execution output found in Ansible events")

        if runner.status == "successful":
            self.logger.info(f"Playbook {playbook_name} completed successfully")
            return execution_output if execution_output else None
        else:
            self.logger.error(f"Playbook {playbook_name} failed with status: {runner.status}")

            # Atomic simulations often capture per-test results before a later task
            # (for example cleanup WinRM errors) fails the playbook. Return partial
            # output so callers can record failed atomics instead of aborting.
            if execution_output and execution_output.get("results"):
                self.logger.warning(
                    "Playbook failed but atomic execution results were captured; "
                    "returning partial execution output"
                )
                execution_output["playbook_status"] = runner.status
                return execution_output

            # Collect error details
            error_details = [f"Playbook failed with status: {runner.status}"]
            
            # Log detailed error information
            if hasattr(runner, 'stats') and runner.stats:
                failures = runner.stats.get('failures', {})
                if failures:
                    error_details.append(f"Failed hosts: {failures}")
                    self.logger.error(f"Failed hosts: {failures}")
                dark = runner.stats.get('dark', {})
                if dark:
                    error_details.append(f"Unreachable hosts: {dark}")
                    self.logger.error(f"Unreachable hosts: {dark}")
            
            # Log events for debugging
            if hasattr(runner, 'events'):
                error_events = []
                for event in runner.events:
                    event_data = event.get('event_data', {})
                    if event.get('event') in ['runner_on_failed', 'runner_on_unreachable', 'runner_on_error']:
                        host = event_data.get('host', 'unknown')
                        task = event_data.get('task', 'unknown')
                        msg = event_data.get('msg', 'No error message')
                        error_events.append(f"Host: {host}, Task: {task}, Error: {msg}")
                
                if error_events:
                    error_details.extend(error_events)
                    self.logger.error("Ansible playbook errors:")
                    for error in error_events[-10:]:  # Show last 10 errors
                        self.logger.error(f"  - {error}")
            
            # Try to read stdout/stderr from the runner's artifact directory
            try:
                stdout_path = os.path.join(self.ansible_dir, 'artifacts', str(runner.config.ident), 'stdout')
                if os.path.exists(stdout_path):
                    with open(stdout_path, 'r') as f:
                        stdout_content = f.read()
                        if stdout_content:
                            # Get last 50 lines of stdout
                            lines = stdout_content.strip().split('\n')
                            last_lines = lines[-50:] if len(lines) > 50 else lines
                            error_details.append("Last Ansible output:")
                            error_details.extend(last_lines)
                            self.logger.error("Last 50 lines of Ansible output:")
                            for line in last_lines:
                                self.logger.error(f"  {line}")
            except Exception as e:
                self.logger.debug(f"Could not read stdout: {e}")
            
            # Raise exception instead of calling sys.exit
            error_msg = "\n".join(error_details)
            raise RuntimeError(f"Ansible playbook execution failed:\n{error_msg}")

    def _get_required_roles_for_playbook(self, playbook_path: str) -> list:
        """
        Extract required roles from a playbook YAML file.
        
        :param playbook_path: Path to the playbook file
        :return: List of role names found in the playbook
        """
        required_roles = []
        try:
            with open(playbook_path, 'r') as f:
                playbook_data = yaml.safe_load(f)
            
            if not playbook_data:
                return required_roles
            
            # Handle both single playbook dict and list of playbooks
            playbooks = playbook_data if isinstance(playbook_data, list) else [playbook_data]
            
            for playbook in playbooks:
                if not isinstance(playbook, dict):
                    continue
                
                # Check for roles at the playbook level
                roles = playbook.get('roles', [])
                for role in roles:
                    if isinstance(role, dict):
                        role_name = role.get('role')
                        if role_name:
                            required_roles.append(role_name)
                    elif isinstance(role, str):
                        required_roles.append(role)
                
                # Check for roles in tasks (for include_role or import_role)
                tasks = playbook.get('tasks', [])
                for task in tasks:
                    if isinstance(task, dict):
                        if 'include_role' in task:
                            role_info = task['include_role']
                            if isinstance(role_info, dict):
                                role_name = role_info.get('name')
                                if role_name:
                                    required_roles.append(role_name)
                            elif isinstance(role_info, str):
                                required_roles.append(role_info)
                        elif 'import_role' in task:
                            role_info = task['import_role']
                            if isinstance(role_info, dict):
                                role_name = role_info.get('name')
                                if role_name:
                                    required_roles.append(role_name)
                            elif isinstance(role_info, str):
                                required_roles.append(role_info)
        except Exception as e:
            self.logger.warning(f"Could not parse playbook {playbook_path} for roles: {e}")
        
        return list(set(required_roles))  # Return unique roles

    def _roles_install_path(self) -> str:
        """Directory where ansible-galaxy installs roles for this attack range."""
        return os.path.join(self.ansible_dir, "roles")

    def _get_local_role_overrides(self) -> dict[str, str]:
        """
        Parse ATTACK_RANGE_LOCAL_ROLES env var (JSON map of galaxy role name -> local path).

        :return: Dict of role name to expanded local filesystem path
        """
        raw = os.environ.get("ATTACK_RANGE_LOCAL_ROLES", "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning(
                "ATTACK_RANGE_LOCAL_ROLES is not valid JSON; ignoring local role overrides"
            )
            return {}
        if not isinstance(parsed, dict):
            self.logger.warning(
                "ATTACK_RANGE_LOCAL_ROLES must be a JSON object; ignoring local role overrides"
            )
            return {}
        overrides: dict[str, str] = {}
        for key, value in parsed.items():
            if isinstance(key, str) and isinstance(value, str) and key and value:
                overrides[key] = os.path.expanduser(value)
        return overrides

    def _resolve_role_dir(self, role_name: str) -> Optional[str]:
        """
        Return the installed role directory for a Galaxy role name, if present.

        Checks terraform/ansible/roles and ~/.ansible/roles using dot and underscore
        directory name variants.
        """
        role_dir_underscore = role_name.replace(".", "_")
        role_dir_dot = role_name
        search_bases = [
            self._roles_install_path(),
            os.path.expanduser("~/.ansible/roles"),
        ]
        for base in search_bases:
            if not os.path.isdir(base):
                continue
            for variant in (role_dir_dot, role_dir_underscore):
                candidate = os.path.join(base, variant)
                if os.path.isdir(candidate):
                    return candidate
        return None

    def _is_bundled_role(self, role_name: str) -> bool:
        """Return True for repo-shipped roles that must not be installed from Galaxy."""
        if not role_name or "." in role_name:
            return False
        role_dir = os.path.join(self._roles_install_path(), role_name)
        tasks_candidates = (
            os.path.join(role_dir, "tasks", "main.yml"),
            os.path.join(role_dir, "tasks", "main.yaml"),
        )
        return any(os.path.isfile(candidate) for candidate in tasks_candidates)

    def _is_role_installed(self, role_name: str) -> bool:
        """
        Check if an Ansible Galaxy role is installed.

        :param role_name: Name of the role (e.g., 'p4t12ick.ar_wireguard_vpn')
        :return: True if role is installed, False otherwise
        """
        return self._resolve_role_dir(role_name) is not None

    def _patch_wireguard_allowed_ips(self) -> None:
        """
        Ensure the WireGuard role's client.j2 uses correct AllowedIPs so VPN clients
        can reach 10.0.2.* (e.g. Splunk). Fixes 10.0.1.1/24, 10.0.2.1/24 -> 10.0.1.0/24, 10.0.2.0/24.
        Idempotent: no-op if already correct.
        """
        role_dir = self._resolve_role_dir(WIREGUARD_GALAXY_ROLE)
        if not role_dir:
            return
        path = os.path.join(role_dir, "templates", "client.j2")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                content = f.read()
            buggy = "AllowedIPs = 10.0.1.1/24, 10.0.2.1/24"
            if buggy in content:
                fixed = "AllowedIPs = {{ vpn_allowed_ips | default('10.0.1.0/24, 10.0.2.0/24') }}"
                with open(path, "w") as f:
                    f.write(content.replace(buggy, fixed))
                self.logger.debug("Patched WireGuard client.j2 AllowedIPs for 10.0.2.0/24 access")
        except OSError as e:
            self.logger.debug(f"Could not patch WireGuard client.j2: {e}")

    def _patch_wireguard_server_config(self) -> None:
        """
        Patch the Galaxy role's wg0.j2: SaveConfig=false and FORWARD rules so both
        client1 and shared clients can reach 10.0.2.*. PreDown for FORWARD uses
        || true so down does not abort if the rule is missing. Idempotent.
        """
        role_dir = self._resolve_role_dir(WIREGUARD_GALAXY_ROLE)
        if not role_dir:
            return
        path = os.path.join(role_dir, "templates", "wg0.j2")
        if not os.path.exists(path):
            return
        # Target: SaveConfig=false, NAT, FORWARD. FORWARD PreDown uses || true to avoid abort when rule missing.
        target = (
            "# false = we manage wg0.conf via Ansible; true would overwrite on restart and drop new peers (e.g. shared clients)\n"
            "SaveConfig = false\n\n"
            "# NAT for VPN clients; FORWARD so VPN->LAN and LAN->VPN work (required for shared clients to reach 10.0.2.*)\n"
            "PostUp = iptables -t nat -I POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE\n"
            "PostUp = iptables -I FORWARD -i wg0 -j ACCEPT\n"
            "PostUp = iptables -I FORWARD -o wg0 -j ACCEPT\n"
            "PreDown = iptables -t nat -D POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE\n"
            "PreDown = iptables -D FORWARD -i wg0 -j ACCEPT || true\n"
            "PreDown = iptables -D FORWARD -o wg0 -j ACCEPT || true"
        )
        try:
            with open(path, "r") as f:
                content = f.read()
            # Original Galaxy block
            old_original = (
                "SaveConfig = true\n\n"
                "# Enable IP forwarding and NAT\n"
                "PostUp = iptables -t nat -I POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE\n"
                "PreDown = iptables -t nat -D POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE"
            )
            # Our previous patch: no FORWARD
            old_no_forward = (
                "# false = we manage wg0.conf via Ansible; true would overwrite on restart and drop new peers (e.g. shared clients)\n"
                "SaveConfig = false\n\n"
                "# NAT for VPN clients going out to internet\n"
                "PostUp = iptables -t nat -I POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE\n"
                "PreDown = iptables -t nat -D POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE"
            )
            # Old FORWARD patch without || true (PreDown could abort if rule missing)
            old_with_forward = (
                "# false = we manage wg0.conf via Ansible; true would overwrite on restart and drop new peers (e.g. shared clients)\n"
                "SaveConfig = false\n\n"
                "# NAT for VPN clients going out to internet; FORWARD so VPN->LAN and LAN->VPN are allowed\n"
                "PostUp = iptables -t nat -I POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE\n"
                "PostUp = iptables -I FORWARD -i wg0 -j ACCEPT\n"
                "PostUp = iptables -I FORWARD -o wg0 -j ACCEPT\n"
                "PreDown = iptables -t nat -D POSTROUTING -o {{ vpn_physical_interface }} -j MASQUERADE\n"
                "PreDown = iptables -D FORWARD -i wg0 -j ACCEPT\n"
                "PreDown = iptables -D FORWARD -o wg0 -j ACCEPT"
            )
            if old_original in content:
                content = content.replace(old_original, target)
            elif old_no_forward in content:
                content = content.replace(old_no_forward, target)
            elif old_with_forward in content:
                content = content.replace(old_with_forward, target)
            else:
                return
            with open(path, "w") as f:
                f.write(content)
            self.logger.debug("Patched WireGuard wg0.j2: SaveConfig=false and FORWARD (PreDown || true)")
        except OSError as e:
            self.logger.debug(f"Could not patch WireGuard wg0.j2: {e}")

    def install_ansible_galaxy_role(self, role_name: str, force: bool = True, max_retries: int = 3) -> bool:
        """
        Install a specific Ansible Galaxy role with retry logic for transient SSL/network errors.

        When ATTACK_RANGE_LOCAL_ROLES maps role_name to a local path, installs from that
        path instead of Ansible Galaxy.

        :param role_name: Name of the role to install (e.g., 'p4t12ick.ar_wireguard_vpn')
        :param force: If True, pass --force to overwrite existing; if False, skip when already installed.
        :param max_retries: Maximum number of retry attempts for transient errors (default: 3)
        :return: True if installation succeeded, False otherwise
        """
        local_overrides = self._get_local_role_overrides()
        local_path = local_overrides.get(role_name)
        if local_path is not None:
            if not os.path.isdir(local_path):
                self.logger.error(
                    f"Local role path for '{role_name}' does not exist or is not a directory: {local_path}"
                )
                return False
            install_target = f"{local_path},{role_name}"
            self.logger.info(
                f"Installing role '{role_name}' from local path '{local_path}' (ATTACK_RANGE_LOCAL_ROLES)"
            )
            max_retries = 1
        else:
            install_target = role_name

        cwd = os.getcwd()
        roles_path = self._roles_install_path()
        try:
            os.chdir(self.ansible_dir)

            cmd = ["ansible-galaxy", "install", install_target, "-p", roles_path]
            if force:
                cmd.append("--force")

            # Retry logic for transient SSL/network errors (Galaxy downloads only)
            for attempt in range(max_retries):
                if attempt > 0:
                    # Exponential backoff: 2^attempt seconds (2, 4, 8 seconds)
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Retrying installation of role '{role_name}' (attempt {attempt + 1}/{max_retries}) after {wait_time} seconds...")
                    time.sleep(wait_time)
                elif local_path is None:
                    self.logger.info(f"Installing role: {role_name}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per attempt
                )

                if result.returncode == 0:
                    self.logger.info(f"Successfully installed role: {role_name}")
                    if result.stdout:
                        self.logger.debug(result.stdout)
                    return True

                # Check if this is a transient SSL/network error that might benefit from retry
                error_output = result.stderr.lower() if result.stderr else ""
                is_transient_error = any(keyword in error_output for keyword in [
                    "ssl", "unexpected_eof", "eof occurred", "connection",
                    "timeout", "temporary failure", "network", "urlopen error"
                ])

                if is_transient_error and attempt < max_retries - 1:
                    # Log warning but continue to retry
                    self.logger.warning(f"Transient error installing role '{role_name}' (attempt {attempt + 1}/{max_retries}): {result.stderr[:200]}")
                    continue
                else:
                    # Final attempt failed or non-transient error
                    self.logger.error(f"Failed to install role '{role_name}': {result.stderr}")
                    if result.stdout:
                        self.logger.error(f"stdout: {result.stdout}")
                    return False

            # Should not reach here, but just in case
            return False
        finally:
            os.chdir(cwd)

    def update_ansible_galaxy_roles(self) -> None:
        """
        Dynamically extract roles from config.yml attack_range section and force install them.
        This ensures all roles used in the configuration are installed before running playbooks.
        """
        # Get attack_range configuration
        attack_range_config = self.config.get("attack_range", [])

        if not attack_range_config:
            self.logger.warning("No attack_range configuration found in config.yml. No roles to install.")
            return

        # Extract unique role names from all entries
        roles_to_install = set()

        for entry in attack_range_config:
            roles = entry.get("roles", [])

            for role in roles:
                if isinstance(role, dict):
                    # Role is a dictionary with 'role' key
                    role_name = role.get("role")
                    if role_name:
                        roles_to_install.add(role_name)
                elif isinstance(role, str):
                    # Role is a string (role name directly)
                    roles_to_install.add(role)

        if not roles_to_install:
            self.logger.warning("No roles found in attack_range configuration. No roles to install.")
            return

        self.logger.info(f"Force installing {len(roles_to_install)} ansible galaxy role(s) from config.yml...")
        self.logger.info(f"Roles to install: {', '.join(sorted(roles_to_install))}")

        failed_roles = []
        for role_name in sorted(roles_to_install):
            if self._is_bundled_role(role_name):
                self.logger.info(f"Using bundled role '{role_name}', skipping Galaxy install")
                continue
            if not self.install_ansible_galaxy_role(role_name):
                failed_roles.append(role_name)

        if failed_roles:
            self.logger.error(f"Failed to install {len(failed_roles)} role(s): {', '.join(failed_roles)}")
            sys.exit(1)

        self.logger.info(f"All {len(roles_to_install)} ansible role(s) installed successfully")

    def _validate_role_directory(self, path: str) -> None:
        """Require a directory with tasks/main.yml or tasks/main.yaml."""
        if not os.path.isdir(path):
            raise ValueError(f"Role path is not a directory: {path}")
        tasks_candidates = (
            os.path.join(path, "tasks", "main.yml"),
            os.path.join(path, "tasks", "main.yaml"),
        )
        if not any(os.path.isfile(candidate) for candidate in tasks_candidates):
            raise ValueError(f"Invalid Ansible role: missing tasks/main.yml at {path}")

    def _resolve_role_name(self, role_path: str, override: Optional[str] = None) -> str:
        """Resolve Galaxy-style role name from meta/main.yml or directory basename."""
        return resolve_local_role_name(role_path, override)

    def _local_roles_dir(self) -> str:
        roles_dir = os.path.join(self.ansible_dir, "roles")
        os.makedirs(roles_dir, exist_ok=True)
        return roles_dir

    def _stage_role_copy(self, role_path: str, role_name: str) -> str:
        """Copy a validated role tree into terraform/ansible/roles/."""
        self._validate_role_directory(role_path)
        roles_dir = self._local_roles_dir()
        dest = os.path.join(roles_dir, role_name)
        if os.path.exists(dest):
            self.logger.warning(f"Overwriting existing staged role at {dest}")
            shutil.rmtree(dest)
        shutil.copytree(role_path, dest)
        self.logger.info(f"Staged local role '{role_name}' at {dest}")
        return role_name

    def _is_safe_tar_member(self, member: tarfile.TarInfo, dest_dir: str) -> bool:
        if member.name.startswith("/") or member.name.startswith("\\"):
            return False
        target = os.path.realpath(os.path.join(dest_dir, member.name))
        dest_real = os.path.realpath(dest_dir)
        return target == dest_real or target.startswith(dest_real + os.sep)

    def _find_extracted_role_root(self, extract_dir: str) -> str:
        try:
            self._validate_role_directory(extract_dir)
            return extract_dir
        except ValueError:
            pass

        entries = [name for name in os.listdir(extract_dir) if not name.startswith(".")]
        if len(entries) == 1:
            candidate = os.path.join(extract_dir, entries[0])
            if os.path.isdir(candidate):
                self._validate_role_directory(candidate)
                return candidate

        for name in entries:
            candidate = os.path.join(extract_dir, name)
            if os.path.isdir(candidate):
                try:
                    self._validate_role_directory(candidate)
                    return candidate
                except ValueError:
                    continue

        raise ValueError("Could not find a valid Ansible role in tarball (expected tasks/main.yml)")

    def _extract_role_tarball(self, tarball_bytes: bytes, dest_dir: str) -> str:
        os.makedirs(dest_dir, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(tarball_bytes), mode="r:*") as tar:
            for member in tar.getmembers():
                if not self._is_safe_tar_member(member, dest_dir):
                    raise ValueError(f"Unsafe path in role tarball: {member.name}")
            extract_kwargs = {}
            if "filter" in tar.extractall.__code__.co_varnames:
                extract_kwargs["filter"] = "data"
            tar.extractall(dest_dir, **extract_kwargs)
        return self._find_extracted_role_root(dest_dir)

    def stage_local_role(self, role_path: str, name: Optional[str] = None) -> str:
        """Validate and stage a local role directory on the Ansible controller."""
        role_path = os.path.abspath(role_path)
        role_name = self._resolve_role_name(role_path, name)
        return self._stage_role_copy(role_path, role_name)

    def stage_local_role_from_tarball(self, content_base64: str, name: Optional[str] = None) -> str:
        """Decode a base64 gzip tarball, extract safely, and stage the role."""
        try:
            tarball_bytes = base64.b64decode(content_base64, validate=True)
        except Exception as exc:
            raise ValueError(f"Invalid base64 role tarball: {exc}") from exc

        if len(tarball_bytes) > LOCAL_ROLE_MAX_TAR_BYTES:
            raise ValueError(
                f"Role tarball exceeds maximum size of {LOCAL_ROLE_MAX_TAR_BYTES} bytes"
            )

        with tempfile.TemporaryDirectory() as extract_dir:
            role_root = self._extract_role_tarball(tarball_bytes, extract_dir)
            role_name = self._resolve_role_name(role_root, name)
            return self._stage_role_copy(role_root, role_name)

    def get_server_become(self, target: str) -> Optional[bool]:
        """
        Return playbook-level become for a target host group.

        None means omit become (default for Windows). True/false set become explicitly.
        """
        attack_range_config = self.config.get("attack_range", [])
        for entry in attack_range_config:
            entry_name = entry.get("name")
            roles = entry.get("roles", [])
            is_match = entry_name == target
            if not is_match:
                for role in roles:
                    if isinstance(role, dict) and role.get("inventory_name") == target:
                        is_match = True
                        break
            if not is_match:
                continue

            is_windows = entry.get("windows", False)
            entry_become = entry.get("become")
            if is_windows:
                return entry_become
            if entry_become is not None:
                return entry_become
            return True

        return True

    def update_apply_roles_playbook(
        self,
        target_host: str,
        role_specs: List[Dict[str, Any]],
        become: Optional[bool],
    ) -> None:
        """Write apply_local_roles.yaml for staged local roles on a single target."""
        playbook_path = os.path.join(self.ansible_dir, APPLY_LOCAL_ROLES_PLAYBOOK)
        play: Dict[str, Any] = {
            "hosts": target_host,
            "roles": [],
        }
        if become is True:
            play["become"] = True
        elif become is False:
            play["become"] = False

        for spec in role_specs:
            role_entry: Dict[str, Any] = {"role": spec["name"]}
            role_vars = spec.get("vars") or {}
            if role_vars:
                role_entry["vars"] = role_vars
            play["roles"].append(role_entry)

        with open(playbook_path, "w", encoding="utf-8") as f:
            yaml.dump([play], f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self.logger.info(
            f"{APPLY_LOCAL_ROLES_PLAYBOOK} generated for target '{target_host}' "
            f"with {len(role_specs)} role(s)"
        )

    def _ci_wireguard_config_path(self) -> str:
        return os.path.join(self.ansible_dir, "client_configs", WG_CI_CLIENT_CONFIG)

    def connect_wireguard_ci(self) -> None:
        """
        Connect to the attack range VPN non-interactively (CI / GitHub Actions).

        Requires wireguard-tools (wg-quick) and passwordless sudo (as on GitHub Actions).
        Uses the generated client config in-place; wg-quick accepts any config path.
        """
        source_config_path = self._ci_wireguard_config_path()
        if not os.path.exists(source_config_path):
            self.logger.error(f"WireGuard config file not found: {source_config_path}")
            sys.exit(1)

        wireguard_config_path = self._prepare_ci_wireguard_config()
        self._ci_wireguard_config_active = wireguard_config_path
        self.logger.info(f"CI mode: bringing up WireGuard from {source_config_path}")
        result = subprocess.run(
            ["sudo", "wg-quick", "up", wireguard_config_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr or result.stdout or "unknown error"
            self.logger.error(f"wg-quick up failed: {detail}")
            self.logger.error(
                "CI WireGuard requires passwordless sudo (GitHub Actions) or run without "
                "ATTACK_RANGE_CI=1 and connect manually when prompted."
            )
            sys.exit(1)

        if not self.wait_for_ssh(WG_CI_ROUTER_IP, timeout=120):
            self.logger.error(f"VPN connected but router {WG_CI_ROUTER_IP} is not reachable")
            sys.exit(1)

        self.logger.info("CI mode: VPN connection established")

    def disconnect_wireguard_ci(self) -> None:
        """Tear down the CI WireGuard interface if it is up."""
        wireguard_config_path = getattr(self, "_ci_wireguard_config_active", None)
        if not wireguard_config_path:
            wireguard_config_path = self._ci_wireguard_config_path()
        if not os.path.exists(wireguard_config_path):
            return
        subprocess.run(
            ["sudo", "wg-quick", "down", wireguard_config_path],
            capture_output=True,
            text=True,
        )
        original = getattr(self, "_ci_wireguard_config_original", None)
        if original is not None:
            with open(self._ci_wireguard_config_path(), "w", encoding="utf-8") as f:
                f.write(original)
            self._ci_wireguard_config_original = None
        self._ci_wireguard_config_active = None

    def prompt_vpn_connection(self) -> None:
        """
        Display the WireGuard configuration and prompt user to connect to VPN.
        Waits for user confirmation before continuing.

        When ATTACK_RANGE_CI=1, connects WireGuard automatically instead of prompting.
        """
        if os.environ.get("ATTACK_RANGE_CI") == "1":
            self.connect_wireguard_ci()
            return

        # Path to the wireguard config file
        wireguard_config_path = os.path.join(self.ansible_dir, "client_configs", "client1.conf")

        if not os.path.exists(wireguard_config_path):
            self.logger.error(f"WireGuard config file not found: {wireguard_config_path}")
            self.logger.error("VPN config generation may have failed. Please check the ansible logs.")
            sys.exit(1)

        # Read the wireguard config
        with open(wireguard_config_path, 'r') as f:
            wireguard_config = f.read()

        # Display the config to the user
        self.logger.info("\n" + "="*80)
        self.logger.info("WireGuard VPN Configuration Generated")
        self.logger.info("="*80)
        self.logger.info("\nPlease use the following WireGuard configuration to connect to the VPN:\n")
        print("\n" + "="*80)
        print("WireGuard VPN Configuration")
        print("="*80)
        print("\n" + wireguard_config)
        print("="*80)
        print(f"\nConfig file location: {wireguard_config_path}")
        print("\nTo connect using WireGuard:")
        print("  1. Copy the configuration above")
        print("  2. Import it into your WireGuard client")
        print("  3. Connect to the VPN")
        print("  4. Once connected, press Enter to continue with lab deployment")
        print("="*80 + "\n")

        # Wait for user confirmation
        self.logger.info("Waiting for user to connect to VPN...")
        input("Press Enter once you have connected to the VPN and are ready to continue with lab deployment...")

        self.logger.info("Continuing with lab deployment...")

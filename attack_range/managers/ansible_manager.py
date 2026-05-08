"""
Ansible manager for Attack Range.

This module handles Ansible operations including inventory management,
playbook updates, and playbook execution.
"""

import json
import os
import sys
import re
import tempfile
import yaml
import time
import socket
import subprocess
import shlex
import logging
import ansible_runner
from typing import Optional, Dict, Any
from attack_range.utils import strip_ansi

# Galaxy role that must always be updated to latest before VPN playbooks (vpn.yaml, vpn_config.yaml)
WIREGUARD_GALAXY_ROLE = "p4t12ick.ar_wireguard_vpn"


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
            roles = server.get("roles", [])

            if not server_name or ip_last_octet is None:
                self.logger.warning(f"Skipping server entry missing name or ip_last_octet: {server}")
                continue

            # Generate IP address
            private_ip = f"10.0.2.{ip_last_octet}"

            # Build host configuration
            host_config = {}

            if is_windows:
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
                    "ansible_winrm_retry_timeout": 600,
                    "ansible_winrm_retry_interval": 10,
                    "ansible_winrm_connection_retries": 3,
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
                    "vpn_allowed_ips": "10.0.1.0/24, 10.0.2.0/24",
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
                    "vpn_allowed_ips": "10.0.1.0/24, 10.0.2.0/24",
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
            entry_become = None
            for entry in attack_range_config:
                entry_name = entry.get("name")
                roles = entry.get("roles", [])
                # Check if this entry matches the hosts_name
                if entry_name == hosts_name:
                    is_windows = entry.get("windows", False)
                    entry_become = entry.get("become")
                    break
                # Check if any role in this entry has inventory_name matching hosts_name
                for role in roles:
                    if isinstance(role, dict) and role.get("inventory_name") == hosts_name:
                        is_windows = entry.get("windows", False)
                        entry_become = entry.get("become")
                        break
                if entry_become is not None or is_windows:
                    break

            # Don't set become: true for Windows hosts, otherwise default to become: true
            if is_windows:
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

        # Ensure required roles for the playbook are installed
        required_roles = self._get_required_roles_for_playbook(playbook_path)
        for role_name in required_roles:
            is_wireguard = role_name == WIREGUARD_GALAXY_ROLE
            if is_wireguard:
                if self._is_role_installed(role_name):
                    continue  # Use existing WireGuard role (no --force) so AllowedIPs fix in ~/.ansible stays
                self.logger.info(f"Installing WireGuard role '{role_name}' from Ansible Galaxy...")
            elif not self._is_role_installed(role_name):
                self.logger.info(f"Installing required role '{role_name}' for playbook '{playbook_name}'")
            else:
                continue
            if not self.install_ansible_galaxy_role(role_name, force=not is_wireguard):
                self.logger.error(f"Failed to install required role '{role_name}' for playbook '{playbook_name}'")
                sys.exit(1)

        if WIREGUARD_GALAXY_ROLE in required_roles:
            self._patch_wireguard_allowed_ips()
            self._patch_wireguard_server_config()

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

        ansible_env = os.environ.copy()
        ansible_env["ANSIBLE_NO_COLOR"] = "1"

        runner = ansible_runner.run(
            private_data_dir=self.ansible_dir,
            cmdline=cmdline,
            playbook=playbook_name,
            verbosity=2,
            envvars=ansible_env,
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
                        msg = strip_ansi(str(event_data.get('msg', 'No error message')))
                        error_events.append(f"Host: {host}, Task: {task}, Error: {msg}")
                
                if error_events:
                    self.logger.error("Ansible playbook errors:")
                    for error in error_events[-10:]:
                        self.logger.error(f"  - {error}")
            
            # Try to read stdout/stderr from the runner's artifact directory
            try:
                stdout_path = os.path.join(self.ansible_dir, 'artifacts', str(runner.config.ident), 'stdout')
                if os.path.exists(stdout_path):
                    with open(stdout_path, 'r') as f:
                        stdout_content = strip_ansi(f.read())
                        if stdout_content:
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

        # Ensure required roles for the playbook are installed
        required_roles = self._get_required_roles_for_playbook(playbook_path)
        for role_name in required_roles:
            is_wireguard = role_name == WIREGUARD_GALAXY_ROLE
            if is_wireguard:
                if self._is_role_installed(role_name):
                    continue  # Use existing WireGuard role (no --force) so AllowedIPs fix in ~/.ansible stays
                self.logger.info(f"Installing WireGuard role '{role_name}' from Ansible Galaxy...")
            elif not self._is_role_installed(role_name):
                self.logger.info(f"Installing required role '{role_name}' for playbook '{playbook_name}'")
            else:
                continue
            if not self.install_ansible_galaxy_role(role_name, force=not is_wireguard):
                error_msg = f"Failed to install required role '{role_name}' for playbook '{playbook_name}'"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

        if WIREGUARD_GALAXY_ROLE in required_roles:
            self._patch_wireguard_allowed_ips()
            self._patch_wireguard_server_config()

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

        ansible_env = os.environ.copy()
        ansible_env["ANSIBLE_NO_COLOR"] = "1"

        runner = ansible_runner.run(
            private_data_dir=self.ansible_dir,
            cmdline=cmdline,
            playbook=playbook_name,
            verbosity=2,
            envvars=ansible_env,
        )

        if extra_vars_path and os.path.exists(extra_vars_path):
            try:
                os.unlink(extra_vars_path)
            except OSError:
                pass

        # Extract execution output from tasks (check both ok and failed events since ignore_errors: True is used)
        execution_output = {}
        output_art_found = False
        events_list = []
        
        if hasattr(runner, 'events') and runner.events:
            # runner.events is a generator, convert to list for processing (only once)
            try:
                events_list = list(runner.events)
                self.logger.debug(f"Processing {len(events_list)} Ansible events")
            except (TypeError, AttributeError):
                # If it's already a list or not iterable, use it directly
                events_list = runner.events if isinstance(runner.events, list) else []
                self.logger.debug(f"Processing events (count unknown - generator or list)")
            
            for event in events_list:
                event_data = event.get('event_data', {})
                event_type = event.get('event', '')
                
                # Look for task results that contain output_art (Atomic Red Team output)
                # Check both runner_on_ok and runner_on_failed since the task uses ignore_errors: True
                if event_type in ['runner_on_ok', 'runner_on_failed']:
                    res = event_data.get('res', {})
                    
                    # Debug: log if we see output_art anywhere
                    if 'output_art' in res:
                        output_art_found = True
                        self.logger.info(f"Found output_art in {event_type} event for task: {event_data.get('task', 'unknown')}")
                    
                    if 'output_art' in res:
                        host = event_data.get('host', 'unknown')
                        output_art = res.get('output_art', {})
                        stdout_lines = output_art.get('stdout_lines', [])
                        stderr_lines = output_art.get('stderr_lines', [])
                        stdout = output_art.get('stdout', '')
                        
                        # Try to get output from any of these sources
                        output_lines = stdout_lines
                        if not output_lines and stderr_lines:
                            output_lines = stderr_lines
                        if not output_lines and stdout:
                            output_lines = stdout.split('\n') if isinstance(stdout, str) else []
                        
                        if output_lines:
                            if host not in execution_output:
                                execution_output[host] = []
                            # Try to get technique from various sources
                            technique = 'unknown'
                            
                            # Method 1: Check event_data for item (from with_items loop)
                            if 'item' in event_data:
                                technique = event_data['item']
                            # Method 2: Check task_vars which contains the item from with_items
                            elif 'task_vars' in event_data:
                                task_vars = event_data.get('task_vars', {})
                                if 'item' in task_vars:
                                    technique = task_vars['item']
                                elif 'technique' in task_vars:
                                    technique = task_vars['technique']
                            # Method 3: Check if we can get it from the task name or args
                            elif 'task' in event_data:
                                task_name = event_data.get('task', '')
                                # The task might have the technique in its name or args
                                task_args = event_data.get('task_args', {})
                                if '_raw_params' in task_args:
                                    technique = task_args['_raw_params']
                            
                            self.logger.info(f"Found execution output for technique {technique} on host {host} ({len(output_lines)} lines)")
                            execution_output[host].append({
                                'technique': technique,
                                'output': output_lines
                            })
        
        # If we didn't find output_art in events, try reading from artifact files
        if not execution_output and hasattr(runner, 'config'):
            try:
                artifact_dir = os.path.join(self.ansible_dir, 'artifacts', str(runner.config.ident))
                if os.path.exists(artifact_dir):
                    self.logger.info(f"Attempting to read output from artifact directory: {artifact_dir}")
                    # Method 1: Try reading from job_events directory
                    job_events_dir = os.path.join(artifact_dir, 'job_events')
                    if os.path.exists(job_events_dir) and os.path.isdir(job_events_dir):
                        self.logger.info("Reading from job_events directory")
                        # Read all event files in the directory
                        for event_file in sorted(os.listdir(job_events_dir)):
                            event_path = os.path.join(job_events_dir, event_file)
                            try:
                                with open(event_path, 'r') as f:
                                    event = json.load(f)
                                    event_data = event.get('event_data', {})
                                    event_type = event.get('event', '')
                                    
                                    if event_type in ['runner_on_ok', 'runner_on_failed']:
                                        res = event_data.get('res', {})
                                        if 'output_art' in res:
                                            host = event_data.get('host', 'unknown')
                                            output_art = res.get('output_art', {})
                                            stdout_lines = output_art.get('stdout_lines', [])
                                            stdout = output_art.get('stdout', '')
                                            
                                            output_lines = stdout_lines
                                            if not output_lines and stdout:
                                                output_lines = stdout.split('\n') if isinstance(stdout, str) else []
                                            
                                            if output_lines:
                                                if host not in execution_output:
                                                    execution_output[host] = []
                                                
                                                # Get technique from task_vars
                                                technique = 'unknown'
                                                task_vars = event_data.get('task_vars', {})
                                                if 'item' in task_vars:
                                                    technique = task_vars['item']
                                                elif 'technique' in task_vars:
                                                    technique = task_vars['technique']
                                                
                                                self.logger.info(f"Found execution output from job_events for technique {technique} on host {host}")
                                                execution_output[host].append({
                                                    'technique': technique,
                                                    'output': output_lines
                                                })
                            except (json.JSONDecodeError, IOError) as e:
                                self.logger.debug(f"Could not parse event file {event_file}: {e}")
                                continue
                    
                    # Method 2: Try parsing stdout file for output_art debug output
                    if not execution_output:
                        stdout_path = os.path.join(artifact_dir, 'stdout')
                        if os.path.exists(stdout_path):
                            self.logger.info("Attempting to extract output from stdout file")
                            try:
                                with open(stdout_path, 'r') as f:
                                    stdout_content = f.read()
                                    # Look for the output_art.stdout_lines pattern in the stdout
                                    # This is a fallback if events don't contain the structured data
                                    # The stdout might have the debug output showing the output_art
                                    if 'output_art.stdout_lines' in stdout_content or 'ok: [' in stdout_content:
                                        # Try to extract the output from the stdout text
                                        # This is a simple approach - look for the pattern
                                        import re
                                        # Look for patterns like: ok: [10.0.2.11] => { "output_art.stdout_lines": [...] }
                                        pattern = r'ok:\s*\[([^\]]+)\]\s*=>\s*\{[^}]*"output_art\.stdout_lines":\s*\[([^\]]+)\]'
                                        matches = re.findall(pattern, stdout_content, re.DOTALL)
                                        if matches:
                                            self.logger.info(f"Found {len(matches)} output patterns in stdout")
                                            for host, output_str in matches:
                                                # Parse the output array
                                                try:
                                                    # Clean up the output string and parse as JSON array
                                                    output_str = output_str.strip()
                                                    # Remove quotes and split by comma if it's a simple list
                                                    output_lines = [line.strip().strip('"').strip("'") for line in output_str.split(',')]
                                                    output_lines = [line for line in output_lines if line]
                                                    
                                                    if output_lines:
                                                        if host not in execution_output:
                                                            execution_output[host] = []
                                                        # We don't have technique from stdout, use first technique from extra_vars
                                                        technique = extra_vars.get('techniques', ['unknown'])[0] if extra_vars and 'techniques' in extra_vars else 'unknown'
                                                        execution_output[host].append({
                                                            'technique': technique,
                                                            'output': output_lines
                                                        })
                                                        self.logger.info(f"Extracted output from stdout for host {host}")
                                                except Exception as e:
                                                    self.logger.debug(f"Could not parse output from stdout: {e}")
                            except Exception as e:
                                self.logger.debug(f"Could not read stdout file: {e}")
            except Exception as e:
                self.logger.debug(f"Could not read from artifact files: {e}")
        
        if execution_output:
            self.logger.info(f"Extracted execution output for {len(execution_output)} host(s)")
        else:
            if output_art_found:
                self.logger.warning("Found output_art in events but couldn't extract output lines")
            else:
                self.logger.warning("No execution output found in Ansible events - output_art not found in any event")
                # Debug: log some sample events to understand structure
                if events_list:
                    # Find all events with output_art or related to the atomic red team task
                    art_related_events = []
                    for e in events_list:
                        event_data = e.get('event_data', {})
                        task_name = event_data.get('task', '')
                        res = event_data.get('res', {})
                        if 'output_art' in res or 'Run specified Atomic Red Team Technique' in task_name or 'Run Atomic Red Team' in task_name:
                            art_related_events.append({
                                'event': e.get('event'),
                                'task': task_name,
                                'res_keys': list(res.keys()) if res else [],
                                'has_output_art': 'output_art' in res
                            })
                    
                    if art_related_events:
                        self.logger.info(f"Found {len(art_related_events)} events related to Atomic Red Team:")
                        for art_event in art_related_events[:5]:  # Show first 5
                            self.logger.info(f"  - Event: {art_event['event']}, Task: {art_event['task']}, Res keys: {art_event['res_keys']}, Has output_art: {art_event['has_output_art']}")
                    else:
                        # Show sample of all ok/failed events
                        sample_events = [e for e in events_list if e.get('event') in ['runner_on_ok', 'runner_on_failed']][:5]
                        for sample in sample_events:
                            event_data = sample.get('event_data', {})
                            task_name = event_data.get('task', 'unknown')
                            res_keys = list(event_data.get('res', {}).keys())
                            self.logger.debug(f"Sample event - Task: {task_name}, Res keys: {res_keys}")

        if runner.status == "successful":
            self.logger.info(f"Playbook {playbook_name} completed successfully")
            # Return execution output if available
            return execution_output if execution_output else None
        else:
            self.logger.error(f"Playbook {playbook_name} failed with status: {runner.status}")
            
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
                        msg = strip_ansi(str(event_data.get('msg', 'No error message')))
                        error_events.append(f"Host: {host}, Task: {task}, Error: {msg}")
                
                if error_events:
                    error_details.extend(error_events)
                    self.logger.error("Ansible playbook errors:")
                    for error in error_events[-10:]:
                        self.logger.error(f"  - {error}")
            
            # Try to read stdout/stderr from the runner's artifact directory
            try:
                stdout_path = os.path.join(self.ansible_dir, 'artifacts', str(runner.config.ident), 'stdout')
                if os.path.exists(stdout_path):
                    with open(stdout_path, 'r') as f:
                        stdout_content = strip_ansi(f.read())
                        if stdout_content:
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

    def _is_role_installed(self, role_name: str) -> bool:
        """
        Check if an Ansible Galaxy role is installed.
        
        :param role_name: Name of the role (e.g., 'p4t12ick.ar_wireguard_vpn')
        :return: True if role is installed, False otherwise
        """
        # Ansible Galaxy installs roles in roles/ directory with format: namespace.rolename
        # The directory name is the role name with dots replaced or kept depending on version
        roles_dir = os.path.join(self.ansible_dir, "roles")
        
        # Check if roles directory exists
        if not os.path.exists(roles_dir):
            return False
        
        # Try different possible directory names
        # Format 1: namespace_rolename (dots replaced with underscores)
        role_dir_underscore = role_name.replace('.', '_')
        # Format 2: namespace.rolename (dots kept)
        role_dir_dot = role_name
        
        # Check both formats
        if os.path.exists(os.path.join(roles_dir, role_dir_underscore)):
            return True
        if os.path.exists(os.path.join(roles_dir, role_dir_dot)):
            return True
        
        # Also check in ~/.ansible/roles (default location)
        home_roles_dir = os.path.expanduser("~/.ansible/roles")
        if os.path.exists(home_roles_dir):
            if os.path.exists(os.path.join(home_roles_dir, role_dir_underscore)):
                return True
            if os.path.exists(os.path.join(home_roles_dir, role_dir_dot)):
                return True
        
        return False

    def _patch_wireguard_allowed_ips(self) -> None:
        """
        Ensure the WireGuard role's client.j2 uses correct AllowedIPs so VPN clients
        can reach 10.0.2.* (e.g. Splunk). Fixes 10.0.1.1/24, 10.0.2.1/24 -> 10.0.1.0/24, 10.0.2.0/24.
        Idempotent: no-op if already correct.
        """
        path = os.path.expanduser("~/.ansible/roles/p4t12ick.ar_wireguard_vpn/templates/client.j2")
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
        path = os.path.expanduser("~/.ansible/roles/p4t12ick.ar_wireguard_vpn/templates/wg0.j2")
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

        :param role_name: Name of the role to install (e.g., 'p4t12ick.ar_wireguard_vpn')
        :param force: If True, pass --force to overwrite existing; if False, skip when already installed.
        :param max_retries: Maximum number of retry attempts for transient errors (default: 3)
        :return: True if installation succeeded, False otherwise
        """
        cwd = os.getcwd()
        try:
            os.chdir(self.ansible_dir)
            
            cmd = ["ansible-galaxy", "install", role_name]
            if force:
                cmd.append("--force")
            
            # Retry logic for transient SSL/network errors
            for attempt in range(max_retries):
                if attempt > 0:
                    # Exponential backoff: 2^attempt seconds (2, 4, 8 seconds)
                    wait_time = 2 ** attempt
                    self.logger.warning(f"Retrying installation of role '{role_name}' (attempt {attempt + 1}/{max_retries}) after {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
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
            if not self.install_ansible_galaxy_role(role_name):
                failed_roles.append(role_name)

        if failed_roles:
            self.logger.error(f"Failed to install {len(failed_roles)} role(s): {', '.join(failed_roles)}")
            sys.exit(1)

        self.logger.info(f"All {len(roles_to_install)} ansible galaxy roles installed successfully")

    def prompt_vpn_connection(self) -> None:
        """
        Display the WireGuard configuration and prompt user to connect to VPN.
        Waits for user confirmation before continuing.
        """
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

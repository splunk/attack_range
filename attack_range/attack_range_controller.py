"""
Attack Range Controller - Main orchestrator for Attack Range infrastructure.

This module provides the main controller class that orchestrates all Attack Range
operations using modular managers for different responsibilities.
"""

import os
import sys
import time
from typing import Callable, Optional
from .logger import setup_logging

# Import managers
from .managers.config_manager import ConfigManager
from .managers.terraform_manager import TerraformManager
from .managers.ansible_manager import AnsibleManager, APPLY_LOCAL_ROLES_PLAYBOOK
from .managers.ssh_manager import SSHManager
from .managers.backend_manager import BackendManager

# Import cloud providers
from .cloud_providers.aws_provider import AWSProvider
from .cloud_providers.azure_provider import AzureProvider
from .cloud_providers.gcp_provider import GCPProvider

# Import utilities
from .utils import get_wireguard_config, get_wireguard_config_for_client


class AttackRangeController:
    """Controller for managing attack range infrastructure using Terraform and Ansible."""

    def __init__(self, config: dict, config_path: str = None):
        """
        Initialize the AttackRangeController.

        :param config: Configuration dictionary containing terraform and ansible settings
        :param config_path: Optional path to the config file (used for hash checking)
        """
        self.config = config
        self.config_path = config_path
        self.logger = setup_logging(
            os.path.join(os.path.dirname(__file__), "../attack_range.log"), "INFO"
        )

        # Detect cloud provider from config
        self.cloud_provider_name = config.get("general", {}).get("cloud_provider", "aws").lower()
        if self.cloud_provider_name not in ["aws", "azure", "gcp"]:
            self.logger.error(f"Unsupported cloud provider: {self.cloud_provider_name}. Supported providers: aws, azure, gcp")
            sys.exit(1)

        # Set up directory paths
        self._setup_directories()

        # Initialize cloud provider
        self._init_cloud_provider()

        # Initialize managers
        self._init_managers()

    def _setup_directories(self) -> None:
        """Set up directory paths based on cloud provider."""
        # Set up terraform working directory based on cloud provider
        if self.cloud_provider_name == "azure":
            self.terraform_dir = os.path.join(os.path.dirname(__file__), "../terraform/azure")
        elif self.cloud_provider_name == "gcp":
            self.terraform_dir = os.path.join(os.path.dirname(__file__), "../terraform/gcp")
        else:  # aws
            self.terraform_dir = os.path.join(os.path.dirname(__file__), "../terraform/aws")

        # Set up ansible directory
        self.ansible_dir = os.path.join(os.path.dirname(__file__), "../terraform/ansible")

        # Path to inventory file
        self.inventory_path = os.path.join(self.ansible_dir, "inventory.yaml")

        # Path to config folder for storing config files
        self.attack_range_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

        # Path to ssh_keys folder
        self.ssh_keys_dir = os.path.join(os.path.dirname(__file__), "../ssh_keys")
        
        # Path to wireguard_config folder
        self.wireguard_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wireguard_config")

    def _init_cloud_provider(self) -> None:
        """Initialize the appropriate cloud provider."""
        if self.cloud_provider_name == "azure":
            self.cloud_provider = AzureProvider(self.config, self.logger)
        elif self.cloud_provider_name == "gcp":
            self.cloud_provider = GCPProvider(self.config, self.logger)
        else:  # aws
            self.cloud_provider = AWSProvider(self.config, self.logger)

    def _init_managers(self) -> None:
        """Initialize all manager instances."""
        # Config manager
        self.config_manager = ConfigManager(
            self.config,
            self.config_path,
            self.attack_range_dir,
            self.logger
        )

        # Terraform manager
        self.terraform_manager = TerraformManager(
            self.terraform_dir,
            self.config,
            self.logger
        )

        # Ansible manager
        self.ansible_manager = AnsibleManager(
            self.ansible_dir,
            self.inventory_path,
            self.config,
            self.cloud_provider_name,
            self.logger
        )

        # SSH manager
        self.ssh_manager = SSHManager(
            self.ssh_keys_dir,
            self.config,
            self.cloud_provider,
            self.logger
        )

        # Backend manager
        self.backend_manager = BackendManager(
            self.terraform_dir,
            self.config,
            self.config_path,
            self.cloud_provider,
            self.logger
        )

    def build(self, two_phase: bool = False) -> None:
        """
        Build the attack range infrastructure.
        
        For CLI: builds everything in one go (two_phase=False)
        For API: builds in two phases - VPN first, then lab after VPN connection (two_phase=True)

        :param two_phase: If True, only build VPN phase and wait. If False, build everything.
        """
        self.logger.info("[action] > build\n")

        # Check if config file path is provided
        if not self.config_path:
            self.logger.error("Config file path not provided. Cannot proceed with build.")
            sys.exit(1)

        # Get or generate attack_range_id (preserve if already exists)
        attack_range_id = self.config_manager.get_or_create_attack_range_id()
        if attack_range_id == self.config.get("general", {}).get("attack_range_id"):
            # ID already existed, log that we're using it
            self.logger.info(f"Using existing attack_range_id: {attack_range_id}")
        else:
            # New ID was generated
            self.logger.info(f"Generated new attack_range_id: {attack_range_id}")

        # Update terraform variables with the updated config (including attack_range_id)
        self.terraform_manager.update_variables()

        # Validate zeek + Azure combination (must be called before other validations)
        self.config_manager.validate_zeek_azure_combination()

        # Validate zeek_monitor configuration
        self.config_manager.validate_zeek_monitor_config()

        # Validate Cisco FMC/FTD is AWS-only
        self.config_manager.validate_cisco_aws_only()

        # Check if attack range with this attack_range_id is already deployed
        config_file_path = os.path.join(self.attack_range_dir, f"{attack_range_id}.yml")
        if os.path.exists(config_file_path):
            # Load the existing config to check its status
            try:
                import yaml
                with open(config_file_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f)
                existing_status = existing_config.get("general", {}).get("status", "")
                
                # Only skip if status indicates infrastructure is already deployed
                if existing_status in ["running", "completed"]:
                    self.logger.warning(
                        f"An attack range with attack_range_id '{attack_range_id}' already exists "
                        f"with status '{existing_status}'. Skipping build to avoid duplicate infrastructure."
                    )
                    sys.exit(0)
                elif existing_status in ["error", "failed"]:
                    self.logger.info(
                        f"Found existing config with status '{existing_status}'. "
                        "Proceeding with new build attempt."
                    )
            except Exception as e:
                # If we can't read the config, log warning but continue
                self.logger.warning(
                    f"Could not read existing config file {config_file_path}: {e}. "
                    "Proceeding with build."
                )

        # Build VPN phase
        router_public_ip, wireguard_config = self.build_vpn_phase(attack_range_id)

        if two_phase:
            # For API: stop here and wait for VPN connection
            self.logger.info("\n" + "="*80)
            self.logger.info("VPN phase completed. Waiting for VPN connection...")
            self.logger.info("="*80)
            self.logger.info(f"Attack Range ID: {attack_range_id}")
            self.logger.info(f"Router Public IP: {router_public_ip}")
            self.logger.info(f"WireGuard config saved in config file: {self.config_path}")
            self.logger.info("="*80 + "\n")
            return router_public_ip, wireguard_config
        else:
            # Install lab Galaxy roles before VPN while public DNS/internet still works
            self.ansible_manager.update_lab_playbook()
            self.ansible_manager.ensure_playbook_roles_installed("lab.yaml")

            # For CLI: prompt user to connect to VPN, then continue with lab phase
            self.ansible_manager.prompt_vpn_connection()
            self.build_lab_phase(attack_range_id, router_public_ip)
            
            self.logger.info("\n" + "="*80)
            self.logger.info("Attack range built successfully!")
            self.logger.info("="*80)
            self.logger.info(f"Attack Range ID: {attack_range_id}")
            self.logger.info(f"Router Public IP: {router_public_ip}")
            self.logger.info(f"Configuration saved to: {config_file_path}")
            self.logger.info("="*80 + "\n")

    def _run_terraform_step(
        self,
        terraform_running_callback: Optional[Callable[[bool], None]],
        step: Callable[[], None],
    ) -> None:
        """Run a Terraform step and report running state via callback."""
        if terraform_running_callback:
            terraform_running_callback(True)
        try:
            step()
        finally:
            if terraform_running_callback:
                terraform_running_callback(False)

    def build_vpn_phase(
        self,
        attack_range_id: str,
        abort_check: Optional[Callable[[], bool]] = None,
        terraform_running_callback: Optional[Callable[[bool], None]] = None,
    ) -> tuple:
        """
        Build VPN infrastructure (Phase 1).
        
        :param attack_range_id: Attack range ID
        :param abort_check: Optional callable(); if it returns True, build is aborted (raises RuntimeError).
        :param terraform_running_callback: Optional callable(bool); called with True before and False after Terraform operations.
        :return: Tuple of (router_public_ip, wireguard_config)
        """
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")
        # Update status to build_vpn
        self.config_manager.update_status("build_vpn")

        # Setup SSH keys (generate locally, upload to cloud provider, update config)
        self.ssh_manager.setup_ssh_keys()
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        # Update terraform variables again after SSH key setup (config was updated)
        self.terraform_manager.update_variables()

        # Save config to config folder with attack_range_id as filename
        self.config_manager.save_config_to_attack_range(attack_range_id)

        # Dynamically extract and force install ansible galaxy roles from config.yml
        self.ansible_manager.update_ansible_galaxy_roles()
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        # Setup remote backend (S3/Azure Storage/GCS) if needed
        backend_was_created = self.backend_manager.setup_remote_backend()

        # If backend was just created, wait for AWS eventual consistency
        if backend_was_created:
            self.logger.info("Waiting 30 seconds for AWS backend resources to become fully available...")
            time.sleep(30)
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        # Initialize terraform
        self._run_terraform_step(
            terraform_running_callback,
            lambda: self.terraform_manager.init(backend_was_created),
        )
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        # Apply terraform
        self._run_terraform_step(
            terraform_running_callback,
            lambda: self.terraform_manager.apply(),
        )
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        # Get router public IP from terraform output
        self.logger.info("Retrieving router public IP from terraform...")
        router_public_ip = self.terraform_manager.get_output("router_public_ip")

        if not router_public_ip:
            self.config_manager.update_status("error", error="Failed to get router public IP from terraform output", error_phase="build_vpn")
            self.logger.error("Failed to get router public IP from terraform output")
            raise RuntimeError("Failed to get router public IP from terraform output")

        self.logger.info(f"Router public IP: {router_public_ip}")

        # Update inventory.yaml with the public IP
        self.ansible_manager.update_inventory(router_public_ip)

        # Update VPN playbook with router public IP and physical interface
        self.ansible_manager.update_vpn_playbook(router_public_ip)

        # Wait for SSH to become available on the router
        if not self.ansible_manager.wait_for_ssh(router_public_ip):
            self.config_manager.update_status("error", error="SSH is not available on router", error_phase="build_vpn")
            self.logger.error("SSH is not available on router. Cannot proceed with VPN setup.")
            raise RuntimeError("SSH is not available on router")
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        # Run VPN ansible playbook (vpn.yaml) to configure WireGuard server
        self.logger.info("Running VPN setup playbook...")
        self.ansible_manager.run_ansible_playbook("vpn.yaml")
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")
        # Generate and run VPN config playbook (vpn_config.yaml) to generate WireGuard client config
        self.ansible_manager.update_vpn_config_playbook()
        self.logger.info("Running VPN config generation playbook...")
        self.ansible_manager.run_ansible_playbook("vpn_config.yaml")

        # Read WireGuard config and save to wireguard_config folder
        wireguard_config = get_wireguard_config(self.ansible_dir, attack_range_id, self.wireguard_config_dir)

        # Store wireguard_config in the config file (in general section as multiline YAML)
        if wireguard_config:
            self.config_manager.update_wireguard_config(wireguard_config)

        # Persist initial vpn_clients for idempotent sharing
        self.config_manager.update_vpn_clients([{"name": "client1", "address": "10.0.1.11/32"}])

        # Update status to wait_for_vpn
        self.config_manager.update_status("wait_for_vpn", router_public_ip=router_public_ip)

        return router_public_ip, wireguard_config

    def build_lab_phase(self, attack_range_id: str, router_public_ip: str = None, abort_check: Optional[Callable[[], bool]] = None) -> None:
        """
        Build lab infrastructure (Phase 2) - after VPN connection.
        
        :param attack_range_id: Attack range ID
        :param router_public_ip: Router public IP (if None, will be retrieved from terraform)
        :param abort_check: Optional callable(); if it returns True, build is aborted (raises RuntimeError).
        """
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")
        # Update status to build_lab
        self.config_manager.update_status("build_lab")

        # Get router public IP if not provided
        if not router_public_ip:
            router_public_ip = self.terraform_manager.get_output("router_public_ip")
            if not router_public_ip:
                self.config_manager.update_status("error", error="Failed to get router public IP from terraform output", error_phase="build_lab")
                self.logger.error("Failed to get router public IP from terraform output")
                raise RuntimeError("Failed to get router public IP from terraform output")
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        try:
            # Update inventory with attack_range servers
            self.ansible_manager.update_inventory_attack_range_servers()

            # Update lab.yaml playbook based on config
            self.ansible_manager.update_lab_playbook()

            # Update inventory password for Windows hosts
            self.ansible_manager.update_inventory_password()

            # Run lab ansible playbook (lab.yaml) to configure attack range servers
            self.logger.info("Running lab deployment playbook...")
            self.ansible_manager.run_ansible_playbook_safe("lab.yaml")
        except (Exception, SystemExit) as e:
            if isinstance(e, SystemExit) and e.code in (0, None):
                raise
            if "Build aborted" in str(e):
                raise
            error_msg = str(e) if not isinstance(e, SystemExit) else "Lab Ansible playbook failed."
            if len(error_msg) > 8000:
                error_msg = error_msg[-8000:]
            self.config_manager.update_status(
                "error",
                error=error_msg,
                error_phase="build_lab",
                router_public_ip=router_public_ip,
            )
            if isinstance(e, SystemExit):
                raise RuntimeError(error_msg) from e
            raise
        if abort_check and abort_check():
            raise RuntimeError("Build aborted")

        # Update status to running
        self.config_manager.update_status("running", router_public_ip=router_public_ip)

    def destroy(self) -> None:
        """
        Destroy the attack range infrastructure using terraform destroy.
        """
        self.logger.info("[action] > destroy\n")

        # Setup remote backend (S3/Azure Storage/GCS) if needed
        self.backend_manager.setup_remote_backend()

        # Initialize terraform for destroy
        self.terraform_manager.init_for_destroy()

        # Destroy terraform infrastructure
        self.terraform_manager.destroy()

        self.logger.info("Attack range destroyed successfully")

        # Clean up SSH keys (delete from cloud provider)
        self.ssh_manager.cleanup_ssh_keys()

        # Clean up remote backend resources
        self.backend_manager.cleanup_remote_backend()

        # Remove config file with attack_range_id from config folder
        if self.config_path:
            self.config_manager.remove_config()

    def simulate(
        self,
        target: str,
        techniques: list | None = None,
        atomics: list | None = None,
        atomic_files: list | None = None,
    ) -> dict:
        """
        Run Atomic Red Team techniques against a target server.
        
        :param target: Target server name (must match a server name in attack_range config)
        :param techniques: List of MITRE ATT&CK technique IDs (e.g., ["T1003.001", "T1059.003"])
        :param atomics: List of dicts with ``technique`` and ``guid`` for individual atomic tests
        :param atomic_files: List of dicts with custom atomic YAML (``path`` or ``content`` on controller)
        :raises ValueError: If validation fails
        :raises RuntimeError: If simulation execution fails
        """
        techniques = techniques or []
        atomics = atomics or []
        atomic_files = atomic_files or []
        if not techniques and not atomics and not atomic_files:
            error_msg = (
                "No techniques, atomics, or atomic files specified. Provide at least one "
                "technique ID, atomic (technique + guid), or atomic file."
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info(
            f"[action] > simulate on target: {target} with techniques: {techniques}, "
            f"atomics: {len(atomics)}, atomic_files: {len(atomic_files)}\n"
        )
        
        # Validate that attack range is running
        status = self.config.get("general", {}).get("status", "")
        if status not in ["running", "completed"]:
            error_msg = f"Cannot run simulation. Attack range status is: {status}. Must be 'running' or 'completed'."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Find the target server in config
        attack_range_config = self.config.get("attack_range", [])
        target_server = None
        for server in attack_range_config:
            if server.get("name") == target:
                target_server = server
                break
        
        if not target_server:
            available_servers = [s.get("name") for s in attack_range_config if s.get("name")]
            error_msg = f"Target server '{target}' not found in attack_range configuration."
            self.logger.error(error_msg)
            self.logger.info("Available servers:")
            for server in attack_range_config:
                self.logger.info(f"  - {server.get('name')}")
            raise ValueError(f"{error_msg} Available servers: {', '.join(available_servers) if available_servers else 'None'}")
        
        # Ensure inventory is up to date with attack range servers
        # We use private IPs from the inventory, so no terraform/router IP needed
        self.ansible_manager.update_inventory_attack_range_servers()
        self.ansible_manager.update_inventory_password()
        
        # Determine target host - use server name as inventory group
        # The target server name should match an inventory group name
        # Verify the inventory group exists
        import yaml
        with open(self.ansible_manager.inventory_path, 'r') as f:
            inventory = yaml.safe_load(f)
        
        if target not in inventory or 'hosts' not in inventory.get(target, {}):
            available_groups = [k for k, v in inventory.items() if isinstance(v, dict) and 'hosts' in v]
            error_msg = f"Inventory group '{target}' not found. Available groups: {', '.join(available_groups) if available_groups else 'None'}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Run the simulation playbook
        self.logger.info(f"Running Atomic Red Team simulation on {target}...")
        if techniques:
            self.logger.info(f"Techniques: {', '.join(techniques)}")
        if atomics:
            self.logger.info(f"Atomics: {len(atomics)} test(s) (technique + guid)")
        if atomic_files:
            self.logger.info(f"Atomic files: {len(atomic_files)} custom YAML file(s)")

        extra_vars = {
            "target_host": target,  # Use server name as inventory group
            "techniques": techniques,
            "atomics": atomics,
            "atomic_files": atomic_files,
        }
        
        # Ensure the p4t12ick.ar_atomic_red_team role is installed
        if not self.ansible_manager._is_role_installed("p4t12ick.ar_atomic_red_team"):
            self.logger.info("Installing p4t12ick.ar_atomic_red_team role from Ansible Galaxy...")
            if not self.ansible_manager.install_ansible_galaxy_role("p4t12ick.ar_atomic_red_team"):
                error_msg = "Failed to install p4t12ick.ar_atomic_red_team role"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        # Run the playbook using the safe method that raises exceptions instead of calling sys.exit
        execution_output = self.ansible_manager.run_ansible_playbook_safe("simulate_atomic_red_team.yml", extra_vars=extra_vars)
        
        self.logger.info(f"\nSimulation completed successfully on {target}")
        
        # Log execution output for debugging
        if execution_output:
            self.logger.info(f"Execution output captured: {execution_output}")
        else:
            self.logger.warning("No execution output was captured from the playbook")
        
        # Return execution output for API response
        return execution_output

    def apply_role(self, target: str, roles: list | None = None) -> dict:
        """
        Stage and execute local Ansible roles against a target server.

        :param target: Target server name (must match a server name in attack_range config)
        :param roles: List of dicts with ``path`` (CLI) or ``content_base64`` (API),
            optional ``name`` override, and optional ``vars``
        :raises ValueError: If validation fails
        :raises RuntimeError: If role staging or playbook execution fails
        """
        roles = roles or []
        if not roles:
            error_msg = "No roles specified. Provide at least one local role."
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.info(
            f"[action] > apply_role on target: {target} with {len(roles)} role(s)\n"
        )

        status = self.config.get("general", {}).get("status", "")
        if status not in ["running", "completed"]:
            error_msg = (
                f"Cannot apply roles. Attack range status is: {status}. "
                "Must be 'running' or 'completed'."
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        attack_range_config = self.config.get("attack_range", [])
        target_server = None
        for server in attack_range_config:
            if server.get("name") == target:
                target_server = server
                break

        if not target_server:
            available_servers = [s.get("name") for s in attack_range_config if s.get("name")]
            error_msg = f"Target server '{target}' not found in attack_range configuration."
            self.logger.error(error_msg)
            raise ValueError(
                f"{error_msg} Available servers: "
                f"{', '.join(available_servers) if available_servers else 'None'}"
            )

        self.ansible_manager.update_inventory_attack_range_servers()
        self.ansible_manager.update_inventory_password()

        import yaml as yaml_lib

        with open(self.ansible_manager.inventory_path, "r", encoding="utf-8") as f:
            inventory = yaml_lib.safe_load(f)

        if target not in inventory or "hosts" not in inventory.get(target, {}):
            available_groups = [
                k for k, v in inventory.items() if isinstance(v, dict) and "hosts" in v
            ]
            error_msg = (
                f"Inventory group '{target}' not found. "
                f"Available groups: {', '.join(available_groups) if available_groups else 'None'}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        role_specs = []
        roles_applied = []
        for role in roles:
            role_path = role.get("path")
            content_base64 = role.get("content_base64")
            name_override = role.get("name")
            role_vars = role.get("vars") or {}

            if role_path and content_base64:
                raise ValueError("Each role must specify either path or content_base64, not both.")
            if not role_path and not content_base64:
                raise ValueError("Each role must specify either path or content_base64.")

            if role_path:
                if not os.path.isdir(role_path):
                    raise ValueError(f"Role path is not a directory: {role_path}")
                resolved_name = self.ansible_manager.stage_local_role(
                    os.path.abspath(role_path), name_override
                )
            else:
                resolved_name = self.ansible_manager.stage_local_role_from_tarball(
                    content_base64, name_override
                )

            roles_applied.append(resolved_name)
            role_specs.append({"name": resolved_name, "vars": role_vars})

        become = self.ansible_manager.get_server_become(target)
        self.ansible_manager.update_apply_roles_playbook(target, role_specs, become)

        self.logger.info(
            f"Running local roles on {target}: {', '.join(roles_applied)}"
        )
        execution_output = self.ansible_manager.run_ansible_playbook_safe(
            APPLY_LOCAL_ROLES_PLAYBOOK
        )

        self.logger.info(f"\nRole apply completed successfully on {target}")

        return {
            "target": target,
            "roles_applied": roles_applied,
            "execution_output": execution_output,
        }

    def share(self, name: str) -> str:
        """
        Share the attack range by generating a new WireGuard client config for the given name.
        Runs the VPN playbooks with updated vpn_clients (existing + new), fetches the new
        client's config, persists it in general.sharing and general.vpn_clients, and returns it.

        :param name: Share name (used as client name, e.g. "alice")
        :return: WireGuard config string for the new client
        :raises ValueError: If validation fails (status, duplicate name, missing router IP)
        :raises RuntimeError: If playbook or file read fails
        """
        self.logger.info(f"[action] > share with name: {name}\n")

        status = self.config.get("general", {}).get("status", "")
        if status not in ["wait_for_vpn", "running"]:
            raise ValueError(
                f"Cannot share. Attack range status is '{status}'. Must be 'wait_for_vpn' or 'running'."
            )

        if not name or not str(name).strip():
            raise ValueError("Share name is required and must be non-empty.")

        name = str(name).strip()

        vpn_clients = self.config.get("general", {}).get("vpn_clients")
        if not vpn_clients:
            vpn_clients = [{"name": "client1", "address": "10.0.1.11/32"}]

        if any(c.get("name") == name for c in vpn_clients):
            raise ValueError(f"A share with the name '{name}' already exists.")

        router_public_ip = self.config.get("general", {}).get("router_public_ip")
        if not router_public_ip:
            raise ValueError("Router public IP not available. Cannot run VPN playbooks.")

        next_octet = 11 + len(vpn_clients)
        new_client = {"name": name, "address": f"10.0.1.{next_octet}/32"}
        new_vpn_clients = list(vpn_clients) + [new_client]

        self.ansible_manager.update_inventory(router_public_ip)
        self.ansible_manager.update_vpn_playbook(router_public_ip)
        self.ansible_manager.update_vpn_config_playbook()

        extra_vars = {"vpn_clients": new_vpn_clients}

        self.logger.info("Running VPN deploy playbook with updated vpn_clients...")
        self.ansible_manager.run_ansible_playbook_safe("vpn.yaml", extra_vars=extra_vars)

        self.logger.info("Running VPN get_config playbook...")
        self.ansible_manager.run_ansible_playbook_safe("vpn_config.yaml", extra_vars=extra_vars)

        config_content = get_wireguard_config_for_client(self.ansible_dir, name)
        if not config_content:
            raise RuntimeError(f"WireGuard config for client '{name}' was not generated.")

        self.config_manager.update_sharing(name, config_content)
        self.config_manager.update_vpn_clients(new_vpn_clients)

        self.logger.info(f"Share '{name}' created successfully. Config saved to general.sharing.")
        return config_content

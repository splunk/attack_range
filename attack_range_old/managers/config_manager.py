"""
Configuration manager for Attack Range.

This module handles configuration validation, attack range ID generation,
and configuration file management.
"""

import os
import sys
import uuid
import yaml
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any


class ConfigManager:
    """Manages Attack Range configuration."""

    def __init__(self, config: dict, config_path: str, attack_range_dir: str, logger: logging.Logger):
        """
        Initialize the configuration manager.

        :param config: Configuration dictionary
        :param config_path: Path to the config file
        :param attack_range_dir: Directory for storing attack range configs
        :param logger: Logger instance
        """
        self.config = config
        self.config_path = config_path
        self.attack_range_dir = attack_range_dir
        self.logger = logger
        self.cloud_provider = config.get("general", {}).get("cloud_provider", "aws").lower()

    def validate_zeek_azure_combination(self) -> None:
        """
        Validate that zeek is not used with Azure cloud provider.
        Zeek is not supported on Azure. Logs a warning and exits if this combination is detected.
        """
        if self.cloud_provider != "azure":
            return

        attack_range_config = self.config.get("attack_range", [])

        # Check if zeek server exists (either zeek: true or name == "zeek")
        zeek_servers = [
            server.get("name")
            for server in attack_range_config
            if server.get("zeek", False) or server.get("name") == "zeek"
        ]

        if zeek_servers:
            self.logger.warning(
                f"WARNING: Zeek is not supported on Azure cloud provider. "
                f"Found zeek server(s): {', '.join(zeek_servers)}. "
                f"Please use AWS cloud provider for zeek functionality."
            )
            self.logger.error("Cannot proceed with build. Zeek + Azure combination is not supported.")
            sys.exit(1)

    def validate_zeek_monitor_config(self) -> None:
        """
        Validate that zeek_monitor is only enabled when a zeek server exists in attack_range.
        Logs a warning if zeek_monitor is enabled but no zeek server is found.
        """
        attack_range_config = self.config.get("attack_range", [])

        # Check if zeek server exists (either zeek: true or name == "zeek")
        zeek_server_exists = any(
            server.get("zeek", False) or server.get("name") == "zeek"
            for server in attack_range_config
        )

        # Find the zeek server configuration
        zeek_server = next(
            (server for server in attack_range_config
             if server.get("zeek", False) or server.get("name") == "zeek"),
            None
        )

        # Check for servers with zeek_monitor enabled
        servers_with_zeek_monitor = [
            server.get("name")
            for server in attack_range_config
            if server.get("zeek_monitor", False)
        ]

        if servers_with_zeek_monitor and not zeek_server_exists:
            self.logger.warning(
                f"zeek_monitor is enabled for server(s): {', '.join(servers_with_zeek_monitor)}, "
                "but no zeek server found in attack_range. "
                "Traffic mirroring will not be configured. "
                "Add a server with zeek: true or name 'zeek' to enable Zeek monitoring."
            )
        elif servers_with_zeek_monitor and zeek_server_exists:
            zeek_server_name = zeek_server.get("name", "zeek")
            self.logger.info(
                f"Zeek monitoring enabled for server(s): {', '.join(servers_with_zeek_monitor)}. "
                f"Zeek server: {zeek_server_name}"
            )

    def validate_cisco_aws_only(self) -> None:
        """
        Validate that Cisco FMC/FTD servers are only used with the AWS provider.
        Marketplace AMIs and multi-NIC FTDv layout are AWS-specific.
        """
        attack_range_config = self.config.get("attack_range", [])
        cisco_servers = [
            server.get("name")
            for server in attack_range_config
            if server.get("cisco_fmc") or server.get("cisco_ftd")
        ]
        if not cisco_servers:
            return

        if self.cloud_provider != "aws":
            self.logger.error(
                "Cisco FMC/FTD deployment is only supported on AWS. "
                f"Found Cisco server(s): {', '.join(str(name) for name in cisco_servers)}."
            )
            sys.exit(1)

        password = str(self.config.get("general", {}).get("attack_range_password") or "")
        if password and not (
            len(password) >= 8
            and any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
        ):
            self.logger.warning(
                "Cisco FMC/FTD admin passwords typically require at least 8 characters "
                "including uppercase, lowercase, and a digit. The current "
                "attack_range_password may be rejected by day-0 configuration."
            )

    def generate_and_set_attack_range_id(self) -> str:
        """
        Generate a new UUID and set it in general.attack_range_id.
        Updates the config dictionary in memory only (not saved to original config file).
        The attack_range_id will be saved to the copied config in the config folder.

        :return: attack_range_id string (UUID)
        """
        if "general" not in self.config:
            self.config["general"] = {}

        # Always generate a new UUID for builds
        attack_range_id = str(uuid.uuid4())
        self.config["general"]["attack_range_id"] = attack_range_id

        # Don't save to original config file - it will be saved to the config folder copy
        self.logger.info(f"Generated new attack_range_id: {attack_range_id} (will be saved to config folder)")

        return attack_range_id

    def get_or_create_attack_range_id(self) -> str:
        """
        Get attack_range_id from config or generate a new UUID if not present.
        Updates the config dictionary in memory only (not saved to original config file).
        The attack_range_id will be saved to the copied config in the config folder.

        :return: attack_range_id string
        """
        if "general" not in self.config:
            self.config["general"] = {}

        attack_range_id = self.config["general"].get("attack_range_id")

        if not attack_range_id:
            # Generate new UUID
            attack_range_id = str(uuid.uuid4())
            self.config["general"]["attack_range_id"] = attack_range_id
            self.logger.info(f"Generated new attack_range_id: {attack_range_id} (will be saved to config folder)")

        return attack_range_id

    def check_config_exists(self) -> bool:
        """
        Check if a config file with the same attack_range_id already exists in config folder.

        :return: True if config with same attack_range_id exists, False otherwise
        """
        attack_range_id = self.get_or_create_attack_range_id()
        if not attack_range_id:
            return False

        config_file_path = os.path.join(self.attack_range_dir, f"{attack_range_id}.yml")
        return os.path.exists(config_file_path)

    def save_config_to_attack_range(self, attack_range_id: str) -> None:
        """
        Save config to config folder with attack_range_id as filename.
        Saves the in-memory config (which includes key_name) to the config folder.

        :param attack_range_id: The attack_range_id to use as filename
        """
        if not attack_range_id:
            self.logger.warning("No attack_range_id provided. Skipping config save.")
            return

        # Ensure config directory exists
        os.makedirs(self.attack_range_dir, exist_ok=True)

        config_file_path = os.path.join(self.attack_range_dir, f"{attack_range_id}.yml")

        try:
            # Save the in-memory config (which includes key_name) to config folder
            with open(config_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            self.logger.info(f"Config saved to config folder: {attack_range_id}.yml (includes key_name)")
        except Exception as e:
            self.logger.error(f"Failed to save config to config folder: {e}")
            sys.exit(1)

    def find_config_files(self) -> List[Tuple[str, str]]:
        """
        Find all .yml files in the config folder.

        :return: List of (attack_range_id, file_path) tuples
        """
        config_files = []
        if not os.path.exists(self.attack_range_dir):
            return config_files

        for filename in os.listdir(self.attack_range_dir):
            if filename.endswith('.yml') and os.path.isfile(os.path.join(self.attack_range_dir, filename)):
                # Extract attack_range_id from filename (remove .yml extension)
                attack_range_id = filename[:-4]  # Remove .yml
                file_path = os.path.join(self.attack_range_dir, filename)
                config_files.append((attack_range_id, file_path))

        return config_files

    def remove_config(self) -> None:
        """
        Remove the config file with attack_range_id as filename from config folder.
        """
        attack_range_id = self.config.get("general", {}).get("attack_range_id")
        if not attack_range_id:
            self.logger.warning("No attack_range_id found in config. Skipping config removal.")
            return

        config_file_path = os.path.join(self.attack_range_dir, f"{attack_range_id}.yml")

        try:
            if os.path.exists(config_file_path):
                os.remove(config_file_path)
                self.logger.info(f"Config file removed: {attack_range_id}.yml")
            else:
                self.logger.warning(f"Config file not found: {attack_range_id}.yml")
        except Exception as e:
            self.logger.error(f"Failed to remove config file: {e}")
            # Don't exit, just log the error and continue

    def get_attack_range_id(self) -> Optional[str]:
        """
        Get the attack_range_id from config.

        :return: attack_range_id string or None
        """
        return self.config.get("general", {}).get("attack_range_id")

    def update_status(self, status: str, **kwargs) -> None:
        """
        Update status and other fields in the config file and in-memory config.
        
        :param status: Status to set (e.g., "running", "wait_for_vpn", "error", etc.)
        :param kwargs: Additional fields to store in general section (e.g., router_public_ip, error, error_phase, etc.)
        """
        if not self.config_path:
            # If no config path, just update in-memory config
            if "general" not in self.config:
                self.config["general"] = {}
            self.config["general"]["status"] = status
            for key, value in kwargs.items():
                if value is not None:
                    self.config["general"][key] = value
            if status not in ["error", "failed"]:
                self.config["general"].pop("error", None)
                self.config["general"].pop("error_phase", None)
            return
        
        try:
            if not os.path.exists(self.config_path):
                return
            
            # Load current config from file
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if "general" not in config:
                config["general"] = {}
            
            config["general"]["status"] = status
            
            # Store additional fields in general section
            for key, value in kwargs.items():
                if value is not None:
                    config["general"][key] = value

            # Drop leftover failure fields when leaving an error state (e.g. lab retry)
            if status not in ["error", "failed"]:
                config["general"].pop("error", None)
                config["general"].pop("error_phase", None)
            
            # Store timestamps
            if status in ["build_vpn", "build_lab", "running"]:
                if "start_time" not in config["general"]:
                    config["general"]["start_time"] = datetime.now().isoformat()
            if status in ["running", "completed", "failed", "error", "aborted"]:
                config["general"]["end_time"] = datetime.now().isoformat()
            
            # Save to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            # Also update in-memory config
            if "general" not in self.config:
                self.config["general"] = {}
            self.config["general"]["status"] = status
            for key, value in kwargs.items():
                if value is not None:
                    self.config["general"][key] = value
            if status not in ["error", "failed"]:
                self.config["general"].pop("error", None)
                self.config["general"].pop("error_phase", None)
                    
        except Exception as e:
            self.logger.warning(f"Failed to update config status in {self.config_path}: {e}")

    def update_wireguard_config(self, wireguard_config: str) -> None:
        """
        Update wireguard_config in the config file and in-memory config as a multiline YAML value.
        
        :param wireguard_config: WireGuard configuration content as a string
        """
        if not wireguard_config:
            return
        
        # Update in-memory config
        if "general" not in self.config:
            self.config["general"] = {}
        self.config["general"]["wireguard_config"] = wireguard_config
        
        if not self.config_path:
            return
        
        try:
            if not os.path.exists(self.config_path):
                return
            
            # Load current config from file
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if "general" not in config:
                config["general"] = {}
            
            # Create a custom YAML representer for literal block scalar (preserves newlines)
            class LiteralStr(str):
                """String that should be represented as literal block scalar (|)"""
                pass
            
            def literal_str_representer(dumper, data):
                """Representer for literal block scalar - preserves exact formatting"""
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            
            # Create a custom Dumper class with our representer
            class CustomDumper(yaml.SafeDumper):
                pass
            
            # Register the representer on the custom dumper
            CustomDumper.add_representer(LiteralStr, literal_str_representer)
            
            # Store wireguard_config in general section as LiteralStr for proper multiline formatting
            config["general"]["wireguard_config"] = LiteralStr(wireguard_config)
            
            # Save to file with custom dumper
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, Dumper=CustomDumper, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            self.logger.info(f"Updated wireguard_config in config file: {self.config_path}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to update wireguard_config in {self.config_path}: {e}")

    def update_sharing(self, name: str, config: str) -> None:
        """
        Add or update a shared WireGuard config in general.sharing.
        general.sharing is a dict mapping share name -> config string.

        :param name: Share name (e.g. "alice")
        :param config: WireGuard configuration content as a string
        """
        if not name or not config:
            return

        if "general" not in self.config:
            self.config["general"] = {}
        if "sharing" not in self.config["general"]:
            self.config["general"]["sharing"] = {}
        self.config["general"]["sharing"][name] = config

        if not self.config_path:
            return

        try:
            if not os.path.exists(self.config_path):
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            if "general" not in config_data:
                config_data["general"] = {}
            if "sharing" not in config_data["general"]:
                config_data["general"]["sharing"] = {}
            config_data["general"]["sharing"][name] = config

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            self.logger.info(f"Updated sharing '{name}' in config file: {self.config_path}")
        except Exception as e:
            self.logger.warning(f"Failed to update sharing in {self.config_path}: {e}")

    def update_vpn_clients(self, vpn_clients: List[Dict[str, Any]]) -> None:
        """
        Persist vpn_clients in general.vpn_clients for idempotent sharing.

        :param vpn_clients: List of {name, address} dicts
        """
        if "general" not in self.config:
            self.config["general"] = {}
        self.config["general"]["vpn_clients"] = vpn_clients

        if not self.config_path:
            return

        try:
            if not os.path.exists(self.config_path):
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            if "general" not in config_data:
                config_data["general"] = {}
            config_data["general"]["vpn_clients"] = vpn_clients

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            self.logger.info(f"Updated vpn_clients in config file: {self.config_path}")
        except Exception as e:
            self.logger.warning(f"Failed to update vpn_clients in {self.config_path}: {e}")

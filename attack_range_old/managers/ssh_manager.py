"""
SSH key manager for Attack Range.

This module handles SSH key generation, storage, and management for cloud providers.
"""

import os
import sys
import subprocess
import logging
from typing import Tuple


class SSHManager:
    """Manages SSH key operations."""

    def __init__(self, ssh_keys_dir: str, config: dict, cloud_provider, logger: logging.Logger):
        """
        Initialize the SSH manager.

        :param ssh_keys_dir: Directory for storing SSH keys
        :param config: Configuration dictionary
        :param cloud_provider: Cloud provider instance (AWSProvider, AzureProvider, or GCPProvider)
        :param logger: Logger instance
        """
        self.ssh_keys_dir = ssh_keys_dir
        self.config = config
        self.cloud_provider = cloud_provider
        self.logger = logger

    def generate_ssh_key_pair(self, key_name: str) -> Tuple[str, str]:
        """
        Generate SSH key pair locally in ssh_keys folder.

        :param key_name: Name for the key pair (will be used as filename)
        :return: Tuple of (private_key_path, public_key_path)
        """
        # Ensure ssh_keys directory exists
        os.makedirs(self.ssh_keys_dir, exist_ok=True)

        private_key_path = os.path.join(self.ssh_keys_dir, f"{key_name}.key")
        # ssh-keygen appends .pub to the full filename, so if we pass {key_name}.key,
        # it creates {key_name}.key.pub. We'll use the base name without extension.
        base_key_path = os.path.join(self.ssh_keys_dir, key_name)
        public_key_path = f"{base_key_path}.pub"
        # Also check for old naming convention (.key.pub)
        old_public_key_path = f"{private_key_path}.pub"

        # Check if keys already exist (try both naming conventions)
        if os.path.exists(private_key_path):
            if os.path.exists(public_key_path):
                self.logger.info(f"SSH key pair already exists: {key_name}")
                return private_key_path, public_key_path
            elif os.path.exists(old_public_key_path):
                # Found old naming convention, use it
                self.logger.info(f"SSH key pair already exists (old naming): {key_name}")
                return private_key_path, old_public_key_path

        self.logger.info(f"Generating SSH key pair: {key_name}")

        # Generate SSH key pair using ssh-keygen
        # Use base_key_path so ssh-keygen creates {key_name} and {key_name}.pub
        # Then we'll rename the private key to {key_name}.key
        try:
            result = subprocess.run(
                [
                    "ssh-keygen",
                    "-t", "rsa",
                    "-b", "4096",
                    "-f", base_key_path,
                    "-N", "",  # No passphrase
                    "-C", f"attack-range-{key_name}"
                ],
                check=True,
                capture_output=True,
                text=True
            )

            # ssh-keygen creates {key_name} and {key_name}.pub
            # Rename {key_name} to {key_name}.key
            generated_private_key = base_key_path
            if os.path.exists(generated_private_key) and generated_private_key != private_key_path:
                os.rename(generated_private_key, private_key_path)

            # Set proper permissions on private key
            os.chmod(private_key_path, 0o600)

            # Verify public key exists
            if not os.path.exists(public_key_path):
                self.logger.error(f"Public key file not found at {public_key_path}")
                sys.exit(1)

            self.logger.info(f"SSH key pair generated successfully: {key_name}")
            return private_key_path, public_key_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to generate SSH key pair: {e.stderr}")
            sys.exit(1)
        except FileNotFoundError:
            self.logger.error("ssh-keygen not found. Please install OpenSSH.")
            sys.exit(1)

    def read_public_key(self, public_key_path: str) -> str:
        """
        Read public key from file.

        :param public_key_path: Path to public key file
        :return: Public key content as string
        """
        try:
            with open(public_key_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            self.logger.error(f"Failed to read public key: {e}")
            sys.exit(1)

    def setup_ssh_keys(self) -> None:
        """
        Setup SSH keys: generate locally, upload to cloud provider, and update config.
        Uses attack_range_id for naming the key pair.
        Always generates key_name from attack_range_id, ignoring any existing key_name in config.
        """
        attack_range_id = self.config.get("general", {}).get("attack_range_id")
        if not attack_range_id:
            self.logger.error("attack_range_id not found in config. Cannot setup SSH keys.")
            sys.exit(1)

        # Always use attack_range_id as key_name, ignore any existing key_name in config
        key_name = attack_range_id

        # Remove any existing key_name from config to ensure we use the generated one
        if "general" in self.config and "key_name" in self.config["general"]:
            old_key_name = self.config["general"]["key_name"]
            if old_key_name != key_name:
                self.logger.info(f"Removing existing key_name '{old_key_name}' from config, using generated '{key_name}'")
            del self.config["general"]["key_name"]

        self.logger.info(f"Setting up SSH keys: key_name={key_name}")

        # Generate SSH key pair locally
        private_key_path, public_key_path = self.generate_ssh_key_pair(key_name)

        # Read public key
        public_key_content = self.read_public_key(public_key_path)

        # Import key to cloud provider (if applicable)
        region = self.cloud_provider.get_region(required=True)
        self.cloud_provider.import_ssh_key(key_name, public_key_content, region)

        # Update config with key_name and key paths
        if "general" not in self.config:
            self.config["general"] = {}

        self.config["general"]["key_name"] = key_name

        # Store absolute paths to keys in memory (for terraform/ansible to use)
        # Use expanduser to handle ~ notation, then abspath for absolute path
        cloud_provider_name = self.config.get("general", {}).get("cloud_provider", "aws").lower()
        
        if cloud_provider_name == "azure":
            if "azure" not in self.config:
                self.config["azure"] = {}
            self.config["azure"]["private_key_path"] = os.path.abspath(os.path.expanduser(private_key_path))
            self.config["azure"]["public_key_path"] = os.path.abspath(os.path.expanduser(public_key_path))
        elif cloud_provider_name == "gcp":
            if "gcp" not in self.config:
                self.config["gcp"] = {}
            self.config["gcp"]["private_key_path"] = os.path.abspath(os.path.expanduser(private_key_path))
            self.config["gcp"]["public_key_path"] = os.path.abspath(os.path.expanduser(public_key_path))
        else:  # aws
            if "aws" not in self.config:
                self.config["aws"] = {}
            self.config["aws"]["private_key_path"] = os.path.abspath(os.path.expanduser(private_key_path))

        # Don't save anything back to the original config file - all dynamic values will be saved to config folder
        self.logger.info(f"SSH keys setup completed. Dynamic values (key_name, attack_range_id, key paths) will be saved to config folder")
        self.logger.info("SSH keys setup completed successfully")

    def cleanup_ssh_keys(self) -> None:
        """
        Cleanup SSH keys: delete from cloud provider and remove local key files.
        Uses attack_range_id for identifying the key pair.
        """
        attack_range_id = self.config.get("general", {}).get("attack_range_id")
        if not attack_range_id:
            self.logger.warning("attack_range_id not found in config. Cannot cleanup SSH keys.")
            return

        key_name = attack_range_id

        self.logger.info(f"Cleaning up SSH keys: key_name={key_name}")

        # Delete key pair from cloud provider (if applicable)
        region = self.cloud_provider.get_region(required=True)
        self.cloud_provider.delete_ssh_key(key_name, region)

        # Delete local key files
        private_key_path = os.path.join(self.ssh_keys_dir, f"{key_name}.key")
        public_key_path = os.path.join(self.ssh_keys_dir, f"{key_name}.pub")

        try:
            if os.path.exists(private_key_path):
                os.remove(private_key_path)
                self.logger.info(f"Deleted local private key: {private_key_path}")
            else:
                self.logger.warning(f"Private key not found: {private_key_path}")

            if os.path.exists(public_key_path):
                os.remove(public_key_path)
                self.logger.info(f"Deleted local public key: {public_key_path}")
            else:
                self.logger.warning(f"Public key not found: {public_key_path}")

        except Exception as e:
            self.logger.warning(f"Failed to delete local key files: {e}")

        self.logger.info("SSH keys cleanup completed successfully")

"""
Backend manager for Attack Range.

This module handles Terraform remote backend setup, including creation and cleanup
of cloud storage resources for state management.
"""

import os
import sys
import logging


class BackendManager:
    """Manages Terraform remote backend operations."""

    def __init__(self, terraform_dir: str, config: dict, config_path: str, cloud_provider, logger: logging.Logger):
        """
        Initialize the backend manager.

        :param terraform_dir: Directory containing Terraform configuration
        :param config: Configuration dictionary
        :param config_path: Path to config file (for backend.tf comments)
        :param cloud_provider: Cloud provider instance (AWSProvider, AzureProvider, or GCPProvider)
        :param logger: Logger instance
        """
        self.terraform_dir = terraform_dir
        self.config = config
        self.config_path = config_path
        self.cloud_provider = cloud_provider
        self.logger = logger

    def setup_remote_backend(self) -> bool:
        """
        Check if remote backend exists, otherwise create it.
        Uses the cloud provider's polymorphic methods for backend operations.

        Returns:
            bool: True if backend resources were just created (fresh setup), False if they already existed
        """
        attack_range_id = self.config.get("general", {}).get("attack_range_id")
        if not attack_range_id:
            self.logger.error("attack_range_id not found in config. Cannot setup remote backend.")
            sys.exit(1)

        config_source = "template/config file"
        if self.config_path:
            config_source = os.path.basename(self.config_path)

        backend_params = self.cloud_provider.get_backend_params(attack_range_id, config_source)
        backend_name = backend_params.backend_name
        region = backend_params.region

        self.logger.info(f"Setting up remote backend: {backend_name}")

        backend_was_created = False
        if not self.cloud_provider.check_backend_exists(backend_name):
            self.logger.info(f"Backend '{backend_name}' does not exist. Creating it...")
            self.cloud_provider.create_backend(backend_name, region)
            backend_was_created = True
        else:
            self.logger.info(f"Backend '{backend_name}' already exists")

        backend_tf_path = os.path.join(self.terraform_dir, "backend.tf")
        self.cloud_provider.write_backend_config(backend_params, backend_tf_path)

        self.logger.info("Remote backend setup completed successfully")
        return backend_was_created

    def cleanup_remote_backend(self) -> None:
        """
        Clean up remote backend resources.
        Uses the cloud provider's polymorphic delete_backend method.
        """
        attack_range_id = self.config.get("general", {}).get("attack_range_id")
        if not attack_range_id:
            self.logger.warning("attack_range_id not found in config. Cannot cleanup remote backend.")
            return

        config_source = "template/config file"
        if self.config_path:
            config_source = os.path.basename(self.config_path)

        backend_params = self.cloud_provider.get_backend_params(attack_range_id, config_source)
        backend_name = backend_params.backend_name
        region = backend_params.region

        self.logger.info(f"Cleaning up remote backend: {backend_name}")
        self.cloud_provider.delete_backend(backend_name, region)
        self.logger.info("Remote backend cleanup completed successfully")

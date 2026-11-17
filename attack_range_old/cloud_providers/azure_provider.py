"""
Azure cloud provider implementation.

This module contains Azure-specific operations for managing storage accounts
and containers.
"""

import sys
import re
from typing import Optional
import os

from .base_provider import BaseCloudProvider, BackendParams

# Azure imports
try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.storage import StorageManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.core.exceptions import AzureError, ResourceNotFoundError
    from azure.storage.blob import BlobServiceClient
    from azure.mgmt.storage.models import StorageAccountCreateParameters, Sku, Kind
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class AzureProvider(BaseCloudProvider):
    """Azure cloud provider implementation."""

    def __init__(self, config: dict, logger):
        """Initialize Azure provider."""
        super().__init__(config, logger)
        if not AZURE_AVAILABLE:
            self.logger.warning("Azure SDK not available. Some features may not work.")

    def get_region(self, required: bool = True) -> Optional[str]:
        """
        Get Azure location from config.

        :param required: If True, raise error if location is not found
        :return: Azure location string or None
        """
        location = self.config.get("azure", {}).get("location")
        if not location and required:
            self.logger.error("Azure location not found in config. Please specify 'azure.location' in your configuration file.")
            sys.exit(1)
        return location

    def get_subscription_id(self, required: bool = True) -> Optional[str]:
        """
        Get Azure subscription ID from config.

        :param required: If True, raise error if not found
        :return: Subscription ID or None
        """
        subscription_id = self.config.get("azure", {}).get("subscription_id")
        if not subscription_id and required:
            self.logger.error("Azure subscription_id not found in config. Please specify 'azure.subscription_id' in your configuration file.")
            sys.exit(1)
        return subscription_id

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize a name to be a valid Azure Storage Account name.
        Storage account names must:
        - Be between 3 and 24 characters
        - Contain only lowercase letters and numbers
        """
        # Convert to lowercase and replace invalid characters with numbers
        sanitized = re.sub(r'[^a-z0-9]', '', name.lower())
        # Ensure minimum length of 3
        if len(sanitized) < 3:
            sanitized = sanitized + '0' * (3 - len(sanitized))
        # Truncate to 24 characters max
        if len(sanitized) > 24:
            sanitized = sanitized[:24]
        return sanitized

    def check_storage_account(self, account_name: str, resource_group_name: str) -> bool:
        """
        Check if an Azure Storage Account exists.

        :param account_name: Name of the storage account
        :param resource_group_name: Name of the resource group
        :return: True if storage account exists, False otherwise
        """
        if not AZURE_AVAILABLE:
            self.logger.warning("Azure SDK not available. Cannot check storage account.")
            return False

        try:
            credential = DefaultAzureCredential()
            subscription_id = self.get_subscription_id(required=False)
            if not subscription_id:
                return False

            storage_client = StorageManagementClient(credential, subscription_id)
            storage_client.storage_accounts.get_properties(resource_group_name, account_name)
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            self.logger.warning(f"Error checking Azure Storage Account '{account_name}': {e}")
            return False

    def create_storage_account(self, account_name: str, resource_group_name: str, location: str) -> None:
        """
        Create an Azure Storage Account for Terraform state storage.

        :param account_name: Name of the storage account to create
        :param resource_group_name: Name of the resource group
        :param location: Azure location where the storage account should be created
        """
        if not AZURE_AVAILABLE:
            self.logger.error("Azure SDK not available. Please install azure-identity and azure-mgmt-storage packages.")
            sys.exit(1)

        try:
            credential = DefaultAzureCredential()
            subscription_id = self.get_subscription_id(required=True)

            # Create resource group if it doesn't exist
            resource_client = ResourceManagementClient(credential, subscription_id)
            try:
                resource_client.resource_groups.get(resource_group_name)
            except ResourceNotFoundError:
                self.logger.info(f"Creating resource group '{resource_group_name}'...")
                resource_client.resource_groups.create_or_update(
                    resource_group_name,
                    {"location": location}
                )

            storage_client = StorageManagementClient(credential, subscription_id)

            # Check if storage account already exists
            try:
                storage_client.storage_accounts.get_properties(resource_group_name, account_name)
                self.logger.info(f"Azure Storage Account '{account_name}' already exists")
                return
            except ResourceNotFoundError:
                pass

            # Create storage account
            storage_parameters = StorageAccountCreateParameters(
                sku=Sku(name="Standard_LRS"),
                kind=Kind.STORAGE_V2,
                location=location
            )

            poller = storage_client.storage_accounts.begin_create(
                resource_group_name,
                account_name,
                storage_parameters
            )
            poller.wait()

            self.logger.info(f"Created Azure Storage Account '{account_name}' in location '{location}'")
        except Exception as e:
            self.logger.error(f"Failed to create Azure Storage Account '{account_name}': {e}")
            sys.exit(1)

    def check_storage_container(self, account_name: str, container_name: str, resource_group_name: str) -> bool:
        """
        Check if an Azure Storage Container exists.

        :param account_name: Name of the storage account
        :param container_name: Name of the container
        :param resource_group_name: Name of the resource group
        :return: True if container exists, False otherwise
        """
        if not AZURE_AVAILABLE:
            return False

        try:
            credential = DefaultAzureCredential()
            subscription_id = self.get_subscription_id(required=False)
            if not subscription_id:
                return False

            storage_client = StorageManagementClient(credential, subscription_id)
            storage_account = storage_client.storage_accounts.get_properties(resource_group_name, account_name)

            # Get storage account keys
            keys = storage_client.storage_accounts.list_keys(resource_group_name, account_name)
            key = keys.keys[0].value

            # Use Azure Storage SDK to check container
            blob_service_client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=key
            )

            container_client = blob_service_client.get_container_client(container_name)
            container_client.get_container_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            self.logger.warning(f"Error checking Azure Storage Container '{container_name}': {e}")
            return False

    def create_storage_container(self, account_name: str, container_name: str, resource_group_name: str) -> None:
        """
        Create an Azure Storage Container for Terraform state.

        :param account_name: Name of the storage account
        :param container_name: Name of the container to create
        :param resource_group_name: Name of the resource group
        """
        if not AZURE_AVAILABLE:
            self.logger.error("Azure SDK not available. Please install azure-storage-blob package.")
            sys.exit(1)

        try:
            credential = DefaultAzureCredential()
            subscription_id = self.get_subscription_id(required=True)

            storage_client = StorageManagementClient(credential, subscription_id)
            storage_account = storage_client.storage_accounts.get_properties(resource_group_name, account_name)

            # Get storage account keys
            keys = storage_client.storage_accounts.list_keys(resource_group_name, account_name)
            key = keys.keys[0].value

            # Use Azure Storage SDK to create container
            blob_service_client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=key
            )

            container_client = blob_service_client.get_container_client(container_name)
            try:
                container_client.create_container()
                self.logger.info(f"Created Azure Storage Container '{container_name}'")
            except Exception as e:
                if "ContainerAlreadyExists" in str(e):
                    self.logger.info(f"Azure Storage Container '{container_name}' already exists")
                else:
                    raise
        except Exception as e:
            self.logger.error(f"Failed to create Azure Storage Container '{container_name}': {e}")
            sys.exit(1)

    def check_backend_exists(self, backend_name: str) -> bool:
        """
        Check if Azure backend (Storage Account + Container) exists.

        :param backend_name: Name of the backend
        :return: True if both storage account and container exist
        """
        storage_account_name = self.sanitize_name(backend_name)
        container_name = "tfstate"
        attack_range_id = self.config.get("general", {}).get("attack_range_id", "")
        resource_group_name = f"rg-terraform-state-{attack_range_id}"

        return self.check_storage_account(storage_account_name, resource_group_name) and \
               self.check_storage_container(storage_account_name, container_name, resource_group_name)

    def create_backend(self, backend_name: str, region: str) -> None:
        """
        Create Azure backend (Storage Account + Container).

        :param backend_name: Name of the backend
        :param region: Azure location
        """
        storage_account_name = self.sanitize_name(backend_name)
        container_name = "tfstate"
        attack_range_id = self.config.get("general", {}).get("attack_range_id", "")
        resource_group_name = f"rg-terraform-state-{attack_range_id}"

        if not self.check_storage_account(storage_account_name, resource_group_name):
            self.create_storage_account(storage_account_name, resource_group_name, region)

        if not self.check_storage_container(storage_account_name, container_name, resource_group_name):
            self.create_storage_container(storage_account_name, container_name, resource_group_name)

    def delete_backend(self, backend_name: str, region: str) -> None:
        """
        Delete Azure backend (Storage Account).

        :param backend_name: Name of the backend
        :param region: Azure location (not used but kept for interface consistency)
        """
        if not AZURE_AVAILABLE:
            self.logger.warning("Azure SDK not available. Cannot delete backend.")
            return

        storage_account_name = self.sanitize_name(backend_name)
        attack_range_id = self.config.get("general", {}).get("attack_range_id", "")
        resource_group_name = f"rg-terraform-state-{attack_range_id}"

        try:
            credential = DefaultAzureCredential()
            subscription_id = self.get_subscription_id(required=False)
            if not subscription_id:
                return

            storage_client = StorageManagementClient(credential, subscription_id)

            # Delete storage account
            if self.check_storage_account(storage_account_name, resource_group_name):
                self.logger.info(f"Deleting Azure Storage Account '{storage_account_name}'...")
                poller = storage_client.storage_accounts.begin_delete(resource_group_name, storage_account_name)
                poller.wait()
                self.logger.info(f"Successfully deleted Azure Storage Account '{storage_account_name}'")
            else:
                self.logger.info(f"Azure Storage Account '{storage_account_name}' does not exist")

            # Delete resource group if empty
            resource_client = ResourceManagementClient(credential, subscription_id)
            try:
                # Check if resource group has any resources
                resources = list(resource_client.resources.list_by_resource_group(resource_group_name))
                if not resources:
                    self.logger.info(f"Deleting empty resource group '{resource_group_name}'...")
                    poller = resource_client.resource_groups.begin_delete(resource_group_name)
                    poller.wait()
                    self.logger.info(f"Successfully deleted resource group '{resource_group_name}'")
            except Exception as e:
                self.logger.warning(f"Could not delete resource group '{resource_group_name}': {e}")

        except Exception as e:
            self.logger.warning(f"Failed to delete Azure backend: {e}")

    def import_ssh_key(self, key_name: str, public_key_content: str, region: str) -> None:
        """
        Azure doesn't require importing keys to a service.
        Keys are used directly in VM configuration.

        :param key_name: Name for the key
        :param public_key_content: Public key content
        :param region: Region (not used for Azure)
        """
        self.logger.info("Azure: SSH keys will be used directly in VM configuration")

    def delete_ssh_key(self, key_name: str, region: str) -> None:
        """
        Azure doesn't store keys in a service, just delete local files.

        :param key_name: Name of the key
        :param region: Region (not used for Azure)
        """
        self.logger.info("Azure: No cloud service keys to delete")

    def write_backend_config(self, backend_params: BackendParams, backend_file_path: str) -> None:
        """
        Update or create backend.tf file with Azure backend configuration.

        :param backend_params: Backend parameters
        :param backend_file_path: Path to the backend.tf file
        """
        storage_account_name = backend_params.azure_storage_account_name
        container_name = backend_params.azure_container_name
        resource_group_name = backend_params.azure_resource_group_name
        location = backend_params.azure_location or backend_params.region
        attack_range_id = backend_params.attack_range_id or 'unknown'
        config_source = backend_params.config_source or 'template/config file'

        backend_config = f'''# This file is AUTO-GENERATED based on the template/config file.
# DO NOT EDIT MANUALLY - changes will be overwritten.
#
# Generated from: {config_source}
# Attack Range ID: {attack_range_id}
# Location: {location} (from azure.location in config)
# Storage Account: {storage_account_name} (derived from attack_range_id)
# Container: {container_name}
# Resource Group: {resource_group_name}
#
# To regenerate this file, run: python main.py build -t <template>
#
terraform {{
  backend "azurerm" {{
    resource_group_name  = "{resource_group_name}"
    storage_account_name = "{storage_account_name}"
    container_name       = "{container_name}"
    key                  = "terraform.tfstate"
  }}
}}
'''

        with open(backend_file_path, 'w') as f:
            f.write(backend_config)

        self.logger.info(f"Backend configuration written to {backend_file_path} (generated from {config_source})")

    def get_backend_params(self, attack_range_id: str, config_source: str = "template/config file") -> BackendParams:
        """
        Get backend parameters for Azure (Storage Account + Container).

        :param attack_range_id: The attack range ID for naming
        :param config_source: Source config file name for backend.tf comments
        :return: Backend parameters
        """
        backend_name = f"terraformstate{attack_range_id.replace('-', '')}"
        storage_account_name = self.sanitize_name(backend_name)
        container_name = "tfstate"
        resource_group_name = f"rg-terraform-state-{attack_range_id}"
        location = self.get_region(required=True)

        return BackendParams(
            backend_name=backend_name,
            azure_storage_account_name=storage_account_name,
            azure_container_name=container_name,
            azure_resource_group_name=resource_group_name,
            azure_location=location,
            region=location,
            attack_range_id=attack_range_id,
            config_source=config_source
        )

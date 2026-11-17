"""
Base cloud provider abstract class.

This module defines the abstract base class for all cloud providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging


@dataclass
class BackendParams:
    """Shared backend parameters for all cloud providers."""

    backend_name: str
    region: str
    attack_range_id: str
    config_source: str = "template/config file"
    aws_bucket_name: Optional[str] = None
    gcp_bucket_name: Optional[str] = None
    gcp_project_id: Optional[str] = None
    azure_storage_account_name: Optional[str] = None
    azure_container_name: Optional[str] = None
    azure_resource_group_name: Optional[str] = None
    azure_location: Optional[str] = None


class BaseCloudProvider(ABC):
    """Abstract base class for cloud providers."""

    def __init__(self, config: dict, logger: logging.Logger):
        """
        Initialize the cloud provider.

        :param config: Configuration dictionary
        :param logger: Logger instance
        """
        self.config = config
        self.logger = logger

    @abstractmethod
    def get_region(self, required: bool = True) -> Optional[str]:
        """
        Get the region/location for the cloud provider.

        :param required: If True, raise error if region is not found
        :return: Region string or None
        """
        pass

    @abstractmethod
    def check_backend_exists(self, backend_name: str) -> bool:
        """
        Check if the backend storage exists.

        :param backend_name: Name of the backend storage
        :return: True if backend exists, False otherwise
        """
        pass

    @abstractmethod
    def create_backend(self, backend_name: str, region: str) -> None:
        """
        Create the backend storage for Terraform state.

        :param backend_name: Name of the backend storage
        :param region: Region where the backend should be created
        """
        pass

    @abstractmethod
    def delete_backend(self, backend_name: str, region: str) -> None:
        """
        Delete the backend storage.

        :param backend_name: Name of the backend storage
        :param region: Region where the backend is located
        """
        pass

    @abstractmethod
    def sanitize_name(self, name: str) -> str:
        """
        Sanitize a name to meet cloud provider naming requirements.

        :param name: Name to sanitize
        :return: Sanitized name
        """
        pass

    @abstractmethod
    def import_ssh_key(self, key_name: str, public_key_content: str, region: str) -> None:
        """
        Import SSH public key to the cloud provider (if applicable).

        :param key_name: Name for the key
        :param public_key_content: Public key content
        :param region: Region for the key
        """
        pass

    @abstractmethod
    def delete_ssh_key(self, key_name: str, region: str) -> None:
        """
        Delete SSH key from the cloud provider (if applicable).

        :param key_name: Name of the key to delete
        :param region: Region where the key is located
        """
        pass

    @abstractmethod
    def write_backend_config(self, backend_params: BackendParams, backend_file_path: str) -> None:
        """
        Save on disk the backend configuration file.

        :param backend_params: Backend parameters for the current provider
        :param backend_file_path: Path to the backend.tf file
        """
        pass

    @abstractmethod
    def get_backend_params(self, attack_range_id: str, config_source: str = "template/config file") -> BackendParams:
        """
        Get backend parameters for the current provider.

        Returns backend parameters with all information needed for backend setup:
        - backend_name: Sanitized name for the storage resource
        - region: Provider-specific region/location
        - All provider-specific parameters needed for write_backend_config()

        :param attack_range_id: The attack range ID for naming
        :param config_source: Source config file name for backend.tf comments
        :return: Backend parameters
        """
        pass

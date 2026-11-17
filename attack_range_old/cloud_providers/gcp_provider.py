"""
GCP cloud provider implementation.

This module contains GCP-specific operations for managing GCS buckets.
"""

import sys
import re
from typing import Optional
import os

from .base_provider import BaseCloudProvider, BackendParams

# GCP imports
try:
    from google.cloud import storage as gcs
    from google.api_core import exceptions as gcp_exceptions
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False


class GCPProvider(BaseCloudProvider):
    """GCP cloud provider implementation."""

    def __init__(self, config: dict, logger):
        """Initialize GCP provider."""
        super().__init__(config, logger)
        if not GCP_AVAILABLE:
            self.logger.warning("GCP SDK not available. Some features may not work.")

    def get_region(self, required: bool = True) -> Optional[str]:
        """
        Get GCP region from config.

        :param required: If True, raise error if region is not found
        :return: GCP region string or None
        """
        region = self.config.get("gcp", {}).get("region")
        if not region and required:
            self.logger.error("GCP region not found in config. Please specify 'gcp.region' in your configuration file.")
            sys.exit(1)
        return region

    def get_project_id(self, required: bool = True) -> Optional[str]:
        """
        Get GCP project ID from config.

        :param required: If True, raise error if not found
        :return: Project ID or None
        """
        project_id = self.config.get("gcp", {}).get("project_id")
        if not project_id and required:
            self.logger.error("GCP project_id not found in config. Please specify 'gcp.project_id' in your configuration file.")
            sys.exit(1)
        return project_id

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize a name to be a valid GCS bucket name.
        GCS bucket names must:
        - Be between 3 and 63 characters
        - Contain only lowercase letters, numbers, dots, and hyphens
        - Start and end with a letter or number
        - Not contain consecutive periods
        """
        # Convert to lowercase and replace invalid characters with hyphens
        sanitized = re.sub(r'[^a-z0-9.-]', '-', name.lower())
        # Remove consecutive dots and hyphens
        sanitized = re.sub(r'[.-]{2,}', '-', sanitized)
        # Remove leading/trailing dots and hyphens
        sanitized = sanitized.strip('.-')
        # Ensure it starts and ends with alphanumeric
        sanitized = re.sub(r'^[^a-z0-9]+', '', sanitized)
        sanitized = re.sub(r'[^a-z0-9]+$', '', sanitized)
        # Ensure minimum length of 3
        if len(sanitized) < 3:
            sanitized = sanitized + '0' * (3 - len(sanitized))
        # Truncate to 63 characters max
        if len(sanitized) > 63:
            sanitized = sanitized[:63].rstrip('.-')
        return sanitized

    def check_gcs_bucket(self, bucket_name: str, project_id: str) -> bool:
        """
        Check if a GCS bucket exists and is accessible.

        :param bucket_name: Name of the GCS bucket
        :param project_id: GCP project ID
        :return: True if bucket exists and is accessible, False otherwise
        """
        if not GCP_AVAILABLE:
            self.logger.warning("GCP SDK not available. Cannot check GCS bucket.")
            return False

        try:
            storage_client = gcs.Client(project=project_id)
            bucket = storage_client.bucket(bucket_name)
            return bucket.exists()
        except Exception as e:
            self.logger.warning(f"Error checking GCS bucket '{bucket_name}': {e}")
            return False

    def create_gcs_bucket(self, bucket_name: str, project_id: str, region: str) -> None:
        """
        Create a GCS bucket for Terraform state storage.

        :param bucket_name: Name of the GCS bucket to create
        :param project_id: GCP project ID
        :param region: GCP region where the bucket should be created
        """
        if not GCP_AVAILABLE:
            self.logger.error("GCP SDK not available. Please install google-cloud-storage package.")
            sys.exit(1)

        try:
            storage_client = gcs.Client(project=project_id)

            # Check if bucket already exists
            bucket = storage_client.bucket(bucket_name)
            if bucket.exists():
                self.logger.info(f"GCS bucket '{bucket_name}' already exists")
                return

            # Create bucket with versioning enabled
            bucket = storage_client.bucket(bucket_name)
            bucket.location = region
            bucket.versioning_enabled = True
            bucket = storage_client.create_bucket(bucket)

            self.logger.info(f"Created GCS bucket '{bucket_name}' in region '{region}'")

        except gcp_exceptions.Conflict:
            self.logger.info(f"GCS bucket '{bucket_name}' already exists")
        except Exception as e:
            self.logger.error(f"Failed to create GCS bucket '{bucket_name}': {e}")
            sys.exit(1)

    def delete_gcs_bucket(self, bucket_name: str, project_id: str) -> None:
        """
        Delete a GCS bucket and all its contents.

        :param bucket_name: Name of the GCS bucket to delete
        :param project_id: GCP project ID
        """
        if not GCP_AVAILABLE:
            self.logger.warning("GCP SDK not available. Cannot delete GCS bucket.")
            return

        try:
            storage_client = gcs.Client(project=project_id)
            bucket = storage_client.bucket(bucket_name)

            # Check if bucket exists
            if not bucket.exists():
                self.logger.info(f"GCS bucket '{bucket_name}' does not exist. Skipping deletion.")
                return

            self.logger.info(f"Deleting GCS bucket '{bucket_name}' and all its contents...")

            # Delete all objects in the bucket (including versions)
            blobs = bucket.list_blobs(versions=True)
            for blob in blobs:
                blob.delete()

            # Now delete the bucket itself
            bucket.delete()
            self.logger.info(f"Successfully deleted GCS bucket '{bucket_name}'")

        except Exception as e:
            self.logger.warning(f"Failed to delete GCS bucket '{bucket_name}': {e}")

    def check_backend_exists(self, backend_name: str) -> bool:
        """
        Check if GCP backend (GCS bucket) exists.

        :param backend_name: Name of the backend
        :return: True if GCS bucket exists
        """
        project_id = self.get_project_id(required=False)
        if not project_id:
            return False

        bucket_name = self.sanitize_name(backend_name)
        return self.check_gcs_bucket(bucket_name, project_id)

    def create_backend(self, backend_name: str, region: str) -> None:
        """
        Create GCP backend (GCS bucket).

        :param backend_name: Name of the backend
        :param region: GCP region
        """
        project_id = self.get_project_id(required=True)
        bucket_name = self.sanitize_name(backend_name)

        if not self.check_gcs_bucket(bucket_name, project_id):
            self.create_gcs_bucket(bucket_name, project_id, region)

    def delete_backend(self, backend_name: str, region: str) -> None:
        """
        Delete GCP backend (GCS bucket).

        :param backend_name: Name of the backend
        :param region: GCP region (not used but kept for interface consistency)
        """
        project_id = self.get_project_id(required=False)
        if not project_id:
            return

        bucket_name = self.sanitize_name(backend_name)
        self.delete_gcs_bucket(bucket_name, project_id)

    def import_ssh_key(self, key_name: str, public_key_content: str, region: str) -> None:
        """
        GCP doesn't require importing keys to a service.
        Keys are used directly in VM configuration.

        :param key_name: Name for the key
        :param public_key_content: Public key content
        :param region: Region (not used for GCP)
        """
        self.logger.info("GCP: SSH keys will be used directly in VM configuration")

    def delete_ssh_key(self, key_name: str, region: str) -> None:
        """
        GCP doesn't store keys in a service, just delete local files.

        :param key_name: Name of the key
        :param region: Region (not used for GCP)
        """
        self.logger.info("GCP: No cloud service keys to delete")

    def write_backend_config(self, backend_params: BackendParams, backend_file_path: str) -> None:
        """
        Update or create backend.tf file with GCP backend configuration.

        :param backend_params: Backend parameters
        :param backend_file_path: Path to the backend.tf file
        """
        bucket_name = backend_params.gcp_bucket_name
        project_id = backend_params.gcp_project_id
        attack_range_id = backend_params.attack_range_id or 'unknown'
        config_source = backend_params.config_source or 'template/config file'

        backend_config = f'''# This file is AUTO-GENERATED based on the template/config file.
# DO NOT EDIT MANUALLY - changes will be overwritten.
#
# Generated from: {config_source}
# Attack Range ID: {attack_range_id}
# Project ID: {project_id} (from gcp.project_id in config)
# Bucket: {bucket_name} (derived from attack_range_id)
#
# To regenerate this file, run: python main.py build -t <template>
#
terraform {{
  backend "gcs" {{
    bucket = "{bucket_name}"
    prefix = "terraform/state"
  }}
}}
'''

        with open(backend_file_path, 'w') as f:
            f.write(backend_config)

        self.logger.info(f"Backend configuration written to {backend_file_path} (generated from {config_source})")

    def get_backend_params(self, attack_range_id: str, config_source: str = "template/config file") -> BackendParams:
        """
        Get backend parameters for GCP (GCS bucket).

        :param attack_range_id: The attack range ID for naming
        :param config_source: Source config file name for backend.tf comments
        :return: Backend parameters
        """
        backend_name = f"terraform-state-{attack_range_id}"
        bucket_name = self.sanitize_name(backend_name)
        project_id = self.get_project_id(required=True)
        region = self.get_region(required=True)

        return BackendParams(
            backend_name=backend_name,
            gcp_bucket_name=bucket_name,
            gcp_project_id=project_id,
            region=region,
            attack_range_id=attack_range_id,
            config_source=config_source
        )

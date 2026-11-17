"""
AWS cloud provider implementation.

This module contains AWS-specific operations for managing S3 buckets
and EC2 key pairs.
"""

import sys
import re
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import os

from .base_provider import BaseCloudProvider, BackendParams


class AWSProvider(BaseCloudProvider):
    """AWS cloud provider implementation."""

    def get_region(self, required: bool = True) -> Optional[str]:
        """
        Get AWS region from config.

        :param required: If True, raise error if region is not found
        :return: AWS region string or None
        """
        region = self.config.get("aws", {}).get("region")
        if not region and required:
            self.logger.error("AWS region not found in config. Please specify 'aws.region' in your configuration file.")
            sys.exit(1)
        return region

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize a name to be a valid S3 bucket name.
        S3 bucket names must:
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

    def check_s3_bucket(self, bucket_name: str, region: str = None) -> bool:
        """
        Check if an S3 bucket exists and is accessible.

        :param bucket_name: Name of the S3 bucket
        :param region: AWS region (optional, defaults to config)
        :return: True if bucket exists and is accessible, False otherwise
        """
        if region is None:
            region = self.get_region(required=True)

        s3_client = boto3.client('s3', region_name=region)
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            elif error_code == '403':
                self.logger.warning(f"Bucket '{bucket_name}' exists but access denied")
                return True
            else:
                return False
        except Exception:
            return False

    def create_s3_bucket(self, bucket_name: str, region: str) -> None:
        """
        Create an S3 bucket for Terraform state storage.

        :param bucket_name: Name of the S3 bucket to create
        :param region: AWS region where the bucket should be created
        """
        s3_client = boto3.client('s3', region_name=region)

        try:
            # us-east-1 doesn't require LocationConstraint
            if region == 'us-east-1':
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )

            # Enable versioning for the bucket (best practice for Terraform state)
            s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )

            # Enable server-side encryption
            s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            )

            self.logger.info(f"Created S3 bucket '{bucket_name}' in region '{region}'")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['BucketAlreadyExists', 'BucketAlreadyOwnedByYou']:
                self.logger.info(f"S3 bucket '{bucket_name}' already exists")
            else:
                self.logger.error(f"Failed to create S3 bucket '{bucket_name}': {e}")
                sys.exit(1)
        except Exception as e:
            self.logger.error(f"Failed to create S3 bucket '{bucket_name}': {e}")
            sys.exit(1)

    def delete_s3_bucket(self, bucket_name: str, region: str) -> None:
        """
        Delete an S3 bucket and all its contents (including versions).

        :param bucket_name: Name of the S3 bucket to delete
        :param region: AWS region
        """
        s3_client = boto3.client('s3', region_name=region)

        try:
            # First, check if bucket exists
            if not self.check_s3_bucket(bucket_name, region):
                self.logger.info(f"S3 bucket '{bucket_name}' does not exist. Skipping deletion.")
                return

            self.logger.info(f"Deleting S3 bucket '{bucket_name}' and all its contents...")

            # Delete all objects and versions
            paginator = s3_client.get_paginator('list_object_versions')
            pages = paginator.paginate(Bucket=bucket_name)

            delete_objects = []
            for page in pages:
                # Delete object versions
                if 'Versions' in page:
                    for version in page['Versions']:
                        delete_objects.append({
                            'Key': version['Key'],
                            'VersionId': version['VersionId']
                        })
                # Delete delete markers
                if 'DeleteMarkers' in page:
                    for marker in page['DeleteMarkers']:
                        delete_objects.append({
                            'Key': marker['Key'],
                            'VersionId': marker['VersionId']
                        })

                # Delete in batches of 1000 (S3 limit)
                while len(delete_objects) > 0:
                    batch = delete_objects[:1000]
                    delete_objects = delete_objects[1000:]
                    if batch:
                        s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': batch}
                        )

            # Also delete regular objects (in case versioning wasn't enabled)
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name)

            delete_objects = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        delete_objects.append({'Key': obj['Key']})

                    # Delete in batches of 1000
                    while len(delete_objects) > 0:
                        batch = delete_objects[:1000]
                        delete_objects = delete_objects[1000:]
                        if batch:
                            s3_client.delete_objects(
                                Bucket=bucket_name,
                                Delete={'Objects': batch}
                            )

            # Now delete the bucket itself
            s3_client.delete_bucket(Bucket=bucket_name)
            self.logger.info(f"Successfully deleted S3 bucket '{bucket_name}'")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchBucket':
                self.logger.info(f"S3 bucket '{bucket_name}' does not exist")
            else:
                self.logger.warning(f"Failed to delete S3 bucket '{bucket_name}': {e}")
        except Exception as e:
            self.logger.warning(f"Failed to delete S3 bucket '{bucket_name}': {e}")

    def check_backend_exists(self, backend_name: str) -> bool:
        """
        Check if AWS backend (S3 bucket) exists.

        :param backend_name: Name of the backend
        :return: True if S3 bucket exists
        """
        region = self.get_region(required=True)
        bucket_name = self.sanitize_name(backend_name)

        return self.check_s3_bucket(bucket_name, region)

    def create_backend(self, backend_name: str, region: str) -> None:
        """
        Create AWS backend (S3 bucket).

        :param backend_name: Name of the backend
        :param region: AWS region
        """
        bucket_name = self.sanitize_name(backend_name)

        if not self.check_s3_bucket(bucket_name, region):
            self.create_s3_bucket(bucket_name, region)

    def delete_backend(self, backend_name: str, region: str) -> None:
        """
        Delete AWS backend (S3 bucket).

        :param backend_name: Name of the backend
        :param region: AWS region
        """
        bucket_name = self.sanitize_name(backend_name)

        self.delete_s3_bucket(bucket_name, region)

    def import_ssh_key(self, key_name: str, public_key_content: str, region: str) -> None:
        """
        Import public key to AWS EC2 as a key pair.

        :param key_name: Name for the key pair in AWS
        :param public_key_content: Public key content as string
        :param region: AWS region
        """
        ec2_client = boto3.client('ec2', region_name=region)

        try:
            # Check if key pair already exists
            try:
                ec2_client.describe_key_pairs(KeyNames=[key_name])
                self.logger.info(f"Key pair '{key_name}' already exists in AWS")
                return
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code != 'InvalidKeyPair.NotFound':
                    raise

            # Import the key pair
            ec2_client.import_key_pair(
                KeyName=key_name,
                PublicKeyMaterial=public_key_content
            )
            self.logger.info(f"Imported key pair '{key_name}' to AWS region '{region}'")

        except Exception as e:
            self.logger.error(f"Failed to import key pair '{key_name}': {e}")
            sys.exit(1)

    def delete_ssh_key(self, key_name: str, region: str) -> None:
        """
        Delete key pair from AWS EC2.

        :param key_name: Name of the key pair to delete
        :param region: AWS region
        """
        ec2_client = boto3.client('ec2', region_name=region)

        try:
            # Check if key pair exists
            try:
                ec2_client.describe_key_pairs(KeyNames=[key_name])
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == 'InvalidKeyPair.NotFound':
                    self.logger.info(f"Key pair '{key_name}' does not exist in AWS")
                    return
                raise

            # Delete the key pair
            ec2_client.delete_key_pair(KeyName=key_name)
            self.logger.info(f"Deleted key pair '{key_name}' from AWS region '{region}'")

        except Exception as e:
            self.logger.warning(f"Failed to delete key pair '{key_name}': {e}")

    def write_backend_config(self, backend_params: BackendParams, backend_file_path: str) -> None:
        """
        Update or create backend.tf file with S3 backend configuration.

        :param backend_params: Backend parameters
        :param backend_file_path: Path to the backend.tf file
        """
        bucket_name = backend_params.aws_bucket_name
        region = backend_params.region
        attack_range_id = backend_params.attack_range_id or 'unknown'
        config_source = backend_params.config_source or 'template/config file'

        backend_config = f'''# This file is AUTO-GENERATED based on the template/config file.
# DO NOT EDIT MANUALLY - changes will be overwritten.
#
# Generated from: {config_source}
# Attack Range ID: {attack_range_id}
# Region: {region} (from aws.region in config)
# Bucket: {bucket_name} (derived from attack_range_id)
#
# To regenerate this file, run: python main.py build -t <template>
#
terraform {{
  backend "s3" {{
    bucket       = "{bucket_name}"
    key          = "terraform.tfstate"
    region       = "{region}"
    use_lockfile = true
    encrypt      = true
  }}
}}
'''

        with open(backend_file_path, 'w') as f:
            f.write(backend_config)

        self.logger.info(f"Backend configuration written to {backend_file_path} (generated from {config_source})")

    def get_backend_params(self, attack_range_id: str, config_source: str = "template/config file") -> BackendParams:
        """
        Get backend parameters for AWS (S3 bucket).

        :param attack_range_id: The attack range ID for naming
        :param config_source: Source config file name for backend.tf comments
        :return: Backend parameters
        """
        backend_name = f"terraform-state-{attack_range_id}"
        bucket_name = self.sanitize_name(backend_name)
        region = self.get_region(required=True)

        return BackendParams(
            backend_name=backend_name,
            aws_bucket_name=bucket_name,
            region=region,
            attack_range_id=attack_range_id,
            config_source=config_source
        )

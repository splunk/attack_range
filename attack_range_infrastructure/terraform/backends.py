"""Terraform state backends.

The generated code only declares the backend type; the settings below are passed to
`terraform init` as `-backend-config` arguments, so rendering never needs cloud access.
The AWS and Azure backends share one state store per account (or subscription) and region,
create it on first use, and never delete it. Each cyber range gets its own state key.
"""

import hashlib
import os
from abc import ABC, abstractmethod
from typing import Optional

from attack_range.application.cyber_range import CyberRange

DEFAULT_KEY_PREFIX = "attack-range"


def _setting(value: Optional[str], variable: str, default: Optional[str] = None) -> Optional[str]:
    return value or os.environ.get(variable) or default


class TerraformBackend(ABC):
    """Where Terraform keeps the state of one cyber range."""

    type: Optional[str] = None
    """Terraform backend type, or None for the default local state file."""

    def __init__(self, key_prefix: Optional[str] = None) -> None:
        self.key_prefix = _setting(key_prefix, "ATTACK_RANGE_STATE_PREFIX", DEFAULT_KEY_PREFIX)

    def state_key(self, cyber_range: CyberRange) -> str:
        if cyber_range.id is None:
            raise ValueError(f"cyber range '{cyber_range.name}' needs an id to keep remote state")
        return f"{self.key_prefix}/{cyber_range.id}/terraform.tfstate"

    @abstractmethod
    def ensure(self, cyber_range: CyberRange) -> None:
        """Create the state store if it does not exist yet."""

    @abstractmethod
    def config(self, cyber_range: CyberRange) -> dict[str, str]:
        """Backend settings for `terraform init -backend-config`."""


class LocalBackend(TerraformBackend):
    """State file next to the generated code."""

    def ensure(self, cyber_range: CyberRange) -> None:
        pass

    def config(self, cyber_range: CyberRange) -> dict[str, str]:
        return {}


class S3Backend(TerraformBackend):
    """State in a versioned, encrypted, private S3 bucket in the region of the cyber range.

    The bucket defaults to `attack-range-tfstate-<account id>-<region>`; set `bucket` or
    ATTACK_RANGE_STATE_BUCKET to use another name. Locking uses S3 lock files (Terraform 1.10+).
    """

    type = "s3"

    def __init__(self, bucket: Optional[str] = None, key_prefix: Optional[str] = None) -> None:
        super().__init__(key_prefix)
        self._bucket = _setting(bucket, "ATTACK_RANGE_STATE_BUCKET")
        self._account_id: Optional[str] = None

    def bucket(self, region: str) -> str:
        if self._bucket:
            return self._bucket
        if self._account_id is None:
            import boto3

            self._account_id = boto3.client("sts", region_name=region).get_caller_identity()["Account"]
        return f"attack-range-tfstate-{self._account_id}-{region}"

    def ensure(self, cyber_range: CyberRange) -> None:
        import boto3
        from botocore.exceptions import ClientError

        region = cyber_range.location
        bucket = self.bucket(region)
        s3 = boto3.client("s3", region_name=region)
        try:
            s3.head_bucket(Bucket=bucket)
            return
        except ClientError as error:
            if error.response["Error"]["Code"] not in ("404", "NoSuchBucket", "NotFound"):
                raise

        create = {"Bucket": bucket}
        if region != "us-east-1":
            create["CreateBucketConfiguration"] = {"LocationConstraint": region}
        try:
            s3.create_bucket(**create)
        except s3.exceptions.BucketAlreadyOwnedByYou:
            return
        s3.get_waiter("bucket_exists").wait(Bucket=bucket)
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        })
        s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}],
        })

    def config(self, cyber_range: CyberRange) -> dict[str, str]:
        return {
            "bucket": self.bucket(cyber_range.location),
            "key": self.state_key(cyber_range),
            "region": cyber_range.location,
            "encrypt": "true",
            "use_lockfile": "true",
        }


class AzureBlobBackend(TerraformBackend):
    """State in a blob container of a private storage account in the location of the cyber range.

    Defaults: resource group `attack-range-tfstate`, container `tfstate`, and a storage account
    named `artfstate<hash of subscription and location>`. Override with the constructor or
    ATTACK_RANGE_STATE_RESOURCE_GROUP and ATTACK_RANGE_STATE_STORAGE_ACCOUNT. The subscription
    comes from ARM_SUBSCRIPTION_ID or AZURE_SUBSCRIPTION_ID. Blob leases provide locking.
    """

    type = "azurerm"

    def __init__(
        self,
        subscription_id: Optional[str] = None,
        resource_group: Optional[str] = None,
        storage_account: Optional[str] = None,
        container: str = "tfstate",
        key_prefix: Optional[str] = None,
    ) -> None:
        super().__init__(key_prefix)
        self._subscription_id = _setting(
            subscription_id, "ARM_SUBSCRIPTION_ID", os.environ.get("AZURE_SUBSCRIPTION_ID")
        )
        self.resource_group = _setting(resource_group, "ATTACK_RANGE_STATE_RESOURCE_GROUP", "attack-range-tfstate")
        self._storage_account = _setting(storage_account, "ATTACK_RANGE_STATE_STORAGE_ACCOUNT")
        self.container = container

    @property
    def subscription_id(self) -> str:
        if not self._subscription_id:
            raise ValueError("Azure state backend needs ARM_SUBSCRIPTION_ID or AZURE_SUBSCRIPTION_ID")
        return self._subscription_id

    def storage_account(self, location: str) -> str:
        if self._storage_account:
            return self._storage_account
        digest = hashlib.sha256(f"{self.subscription_id}/{location}".encode()).hexdigest()
        return f"artfstate{digest[:15]}"

    def ensure(self, cyber_range: CyberRange) -> None:
        from azure.core.exceptions import ResourceNotFoundError
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.resource import ResourceManagementClient
        from azure.mgmt.storage import StorageManagementClient
        from azure.mgmt.storage.models import BlobContainer, Sku, StorageAccountCreateParameters

        location = cyber_range.location
        account = self.storage_account(location)
        credential = DefaultAzureCredential()

        resources = ResourceManagementClient(credential, self.subscription_id)
        if not resources.resource_groups.check_existence(self.resource_group):
            resources.resource_groups.create_or_update(self.resource_group, {"location": location})

        storage = StorageManagementClient(credential, self.subscription_id)
        try:
            storage.storage_accounts.get_properties(self.resource_group, account)
        except ResourceNotFoundError:
            storage.storage_accounts.begin_create(self.resource_group, account, StorageAccountCreateParameters(
                location=location,
                sku=Sku(name="Standard_LRS"),
                kind="StorageV2",
                minimum_tls_version="TLS1_2",
                allow_blob_public_access=False,
                enable_https_traffic_only=True,
            )).result()
        try:
            storage.blob_containers.get(self.resource_group, account, self.container)
        except ResourceNotFoundError:
            storage.blob_containers.create(self.resource_group, account, self.container, BlobContainer())

    def config(self, cyber_range: CyberRange) -> dict[str, str]:
        return {
            "subscription_id": self.subscription_id,
            "resource_group_name": self.resource_group,
            "storage_account_name": self.storage_account(cyber_range.location),
            "container_name": self.container,
            "key": self.state_key(cyber_range),
        }

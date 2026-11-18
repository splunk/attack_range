from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from attack_range_infrastructure.terraform import AzureBlobBackend, S3Backend
from conftest import load_cyber_range, registered


@pytest.fixture(autouse=True)
def no_state_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "ATTACK_RANGE_STATE_PREFIX",
        "ATTACK_RANGE_STATE_BUCKET",
        "ATTACK_RANGE_STATE_RESOURCE_GROUP",
        "ATTACK_RANGE_STATE_STORAGE_ACCOUNT",
        "ARM_SUBSCRIPTION_ID",
        "AZURE_SUBSCRIPTION_ID",
    ):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(variable, "testing")
    monkeypatch.delenv("AWS_PROFILE", raising=False)


@mock_aws
def test_s3_creates_shared_bucket(aws_credentials, ar_template_dir: Path) -> None:
    cyber_range = registered(load_cyber_range(ar_template_dir, "aws"))
    backend = S3Backend()

    backend.ensure(cyber_range)
    backend.ensure(cyber_range)

    bucket = "attack-range-tfstate-123456789012-eu-central-1"
    s3 = boto3.client("s3", region_name="eu-central-1")
    assert s3.get_bucket_versioning(Bucket=bucket)["Status"] == "Enabled"
    assert s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]["BlockPublicPolicy"]
    assert s3.get_bucket_location(Bucket=bucket)["LocationConstraint"] == "eu-central-1"
    assert backend.config(cyber_range) == {
        "bucket": bucket,
        "key": f"attack-range/{cyber_range.id}/terraform.tfstate",
        "region": "eu-central-1",
        "encrypt": "true",
        "use_lockfile": "true",
    }


def test_s3_settings_from_environment(monkeypatch: pytest.MonkeyPatch, ar_template_dir: Path) -> None:
    monkeypatch.setenv("ATTACK_RANGE_STATE_BUCKET", "team-state")
    monkeypatch.setenv("ATTACK_RANGE_STATE_PREFIX", "alice")

    cyber_range = registered(load_cyber_range(ar_template_dir, "aws"))
    config = S3Backend().config(cyber_range)

    assert config["bucket"] == "team-state"
    assert config["key"] == f"alice/{cyber_range.id}/terraform.tfstate"


def test_azure_defaults(monkeypatch: pytest.MonkeyPatch, lab_dir: Path) -> None:
    monkeypatch.setenv("ARM_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000000")

    cyber_range = registered(load_cyber_range(lab_dir, "azure"))
    config = AzureBlobBackend().config(cyber_range)

    account = config["storage_account_name"]
    assert account.startswith("artfstate") and len(account) == 24 and account.isalnum()
    assert config == {
        "subscription_id": "00000000-0000-0000-0000-000000000000",
        "resource_group_name": "attack-range-tfstate",
        "storage_account_name": account,
        "container_name": "tfstate",
        "key": f"attack-range/{cyber_range.id}/terraform.tfstate",
    }


def test_state_key_needs_an_id(ar_template_dir: Path) -> None:
    with pytest.raises(ValueError, match="needs an id"):
        S3Backend(bucket="state").config(load_cyber_range(ar_template_dir, "aws"))


def test_azure_needs_subscription(lab_dir: Path) -> None:
    with pytest.raises(ValueError, match="ARM_SUBSCRIPTION_ID"):
        AzureBlobBackend().config(registered(load_cyber_range(lab_dir, "azure")))

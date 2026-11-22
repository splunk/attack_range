"""
Regression tests for Azure provider SDK compatibility.

azure-mgmt-resource >= 24 moved ResourceManagementClient into the "resources"
subpackage, and azure-mgmt-storage >= 25 models are MutableMappings (so `.keys`
is the dict method, not the key list). Both broke the Azure backend setup.
"""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.modules.setdefault("ansible_runner", MagicMock())
sys.modules.setdefault("python_vagrant", MagicMock())

import pytest

azure_provider = pytest.importorskip("attack_range.cloud_providers.azure_provider")


def test_azure_sdk_imports_succeed():
    """All Azure SDK imports must succeed with the pinned requirements."""
    assert azure_provider.AZURE_AVAILABLE, f"Azure SDK import failed: {azure_provider.AZURE_IMPORT_ERROR}"


def test_first_storage_key_with_mapping_model():
    """azure-mgmt-storage >= 25 returns dict-like models."""
    from azure.mgmt.storage.models import StorageAccountListKeysResult

    result = StorageAccountListKeysResult({"keys": [{"keyName": "key1", "value": "secret1"}]})
    assert azure_provider._first_storage_key(result) == "secret1"


def test_first_storage_key_with_attribute_model():
    """Older msrest-based models expose keys only as an attribute."""
    result = SimpleNamespace(keys=[SimpleNamespace(value="secret1")])
    assert azure_provider._first_storage_key(result) == "secret1"

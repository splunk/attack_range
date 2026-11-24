"""Publish a VHD with the Azure CLI: resource group, storage account, page blob, and managed image."""

import subprocess
from typing import Callable
from urllib.parse import quote

from attack_range.application.images import ImageUpload, ImageUploadError
from attack_range.application.provisioner import NullProvisionLog, ProvisionLog

AzCommand = Callable[[list[str], bool], str]


class AzureCliImageUploader:
    """Runs the Azure CLI steps that turn a local VHD into a managed image.

    The blob upload uses the storage account key. Creating the account grants that access,
    so the command does not wait for a role assignment.
    """

    def __init__(self, run: AzCommand | None = None, log: ProvisionLog | None = None) -> None:
        self._log = log if log is not None else NullProvisionLog()
        self._run = run if run is not None else self._run_az

    def upload(self, image: ImageUpload) -> str:
        self._run(["az", "group", "create", "--name", image.resource_group, "--location", image.region], False)
        self._run([
            "az", "storage", "account", "create",
            "--resource-group", image.resource_group,
            "--name", image.storage_account,
            "--location", image.region,
            "--sku", "Standard_LRS",
            "--kind", "StorageV2",
            "--allow-blob-public-access", "false",
        ], False)
        self._run([
            "az", "storage", "container", "create",
            "--account-name", image.storage_account,
            "--name", image.container,
            "--auth-mode", "key",
        ], False)
        self._run([
            "az", "storage", "blob", "upload",
            "--account-name", image.storage_account,
            "--container-name", image.container,
            "--name", image.blob_name,
            "--file", str(image.vhd),
            "--type", "page",
            "--auth-mode", "key",
        ], True)
        source = (
            f"https://{image.storage_account}.blob.core.windows.net/"
            f"{quote(image.container)}/{quote(image.blob_name)}"
        )
        image_id = self._run([
            "az", "image", "create",
            "--resource-group", image.resource_group,
            "--name", image.image_name,
            "--location", image.region,
            "--source", source,
            "--os-type", image.os_type,
            "--hyper-v-generation", image.hyper_v_generation,
            "--query", "id",
            "--output", "tsv",
        ], False).strip()
        if not image_id.startswith("/subscriptions/"):
            raise ImageUploadError("az image create did not return an image id")
        return image_id

    def _run_az(self, args: list[str], stream: bool) -> str:
        return run_az(args, stream, self._log)


def run_az(args: list[str], stream: bool, log: ProvisionLog | None = None) -> str:
    """Run one az command. `stream` prints each line as it arrives and returns no stdout."""
    output = log if log is not None else NullProvisionLog()
    try:
        if stream:
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        else:
            completed = subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        raise ImageUploadError("az, the Azure CLI, was not found") from error
    if stream:
        assert process.stdout is not None
        for line in process.stdout:
            output.line(line.rstrip("\n"))
        if process.wait() != 0:
            raise ImageUploadError(f"{' '.join(args[:3])} failed")
        return ""
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ImageUploadError(detail or f"{' '.join(args[:3])} failed")
    return completed.stdout

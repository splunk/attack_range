"""Port for turning a local VHD into a provider image."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ImageUploadError(RuntimeError):
    """Raised when a VHD cannot be published as an image."""


@dataclass(frozen=True)
class ImageUpload:
    """One VHD and the Azure resources that will hold it."""

    vhd: Path
    region: str
    os_type: str
    hyper_v_generation: str
    resource_group: str
    storage_account: str
    container: str
    blob_name: str
    image_name: str


class ImageUploader(Protocol):
    """Publishes a VHD and returns the managed image resource id."""

    def upload(self, image: ImageUpload) -> str:
        """Create the Azure resources and return the image id."""

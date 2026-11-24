"""Publish a local VHD as an Azure managed image."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from attr import define

from attack_range.application.images import ImageUpload, ImageUploader, ImageUploadError
from attack_range.application.names import resource_name

OsType = Literal["Linux", "Windows"]
HyperVGeneration = Literal["V1", "V2"]
_STEM = re.compile(r"[^a-z0-9]+")
_STORAGE_ACCOUNT_LIMIT = 24
_IMAGE_NAME_LIMIT = 80
_CONTAINER_NAME_LIMIT = 63
_RESOURCE_GROUP_LIMIT = 90


@dataclass(frozen=True)
class UploadImageInputDto:
    """A VHD to publish in one Azure region."""

    path: Path
    region: str
    user_name: str
    os_type: OsType = "Linux"
    hyper_v_generation: HyperVGeneration = "V1"


@dataclass(frozen=True)
class UploadImageOutputDto:
    """The managed image created from a VHD."""

    success: bool
    path: Path
    region: str = ""
    image_id: str = ""
    resource_group: str = ""
    image_name: str = ""
    error: str | None = None


class UploadImageOutputBoundary:
    """Driven port for the result of an image upload."""

    def present(self, output_dto: UploadImageOutputDto) -> None:
        """Show the outcome of one upload."""


@define
class UploadImage:
    """Upload a VHD as a page blob and create a managed image from it."""

    _output_boundary: UploadImageOutputBoundary
    _uploader: ImageUploader

    def execute(self, input_dto: UploadImageInputDto) -> None:
        try:
            _check_vhd(input_dto.path)
            identity = str(uuid4()).split("-", 1)[0]
            stem = _image_stem(input_dto.path)
            image = ImageUpload(
                vhd=input_dto.path,
                region=input_dto.region,
                os_type=input_dto.os_type,
                hyper_v_generation=input_dto.hyper_v_generation,
                resource_group=resource_name("images", identity, input_dto.user_name, limit=_RESOURCE_GROUP_LIMIT),
                storage_account=storage_account_name(identity, input_dto.user_name),
                container=resource_name("vhds", identity, input_dto.user_name, limit=_CONTAINER_NAME_LIMIT),
                blob_name=input_dto.path.name,
                image_name=resource_name(stem, identity, input_dto.user_name, limit=_IMAGE_NAME_LIMIT),
            )
            image_id = self._uploader.upload(image)
        except (ImageUploadError, OSError, ValueError) as error:
            self._output_boundary.present(UploadImageOutputDto(
                success=False, path=input_dto.path, region=input_dto.region, error=str(error),
            ))
            return
        self._output_boundary.present(UploadImageOutputDto(
            success=True,
            path=input_dto.path,
            region=input_dto.region,
            image_id=image_id,
            resource_group=image.resource_group,
            image_name=image.image_name,
        ))


def storage_account_name(identity: str, user_name: str) -> str:
    """Storage account name `img<identity><user>`, letters and digits only, at most 24 characters.

    The identity stays so two uploads do not share an account. The user name is shortened to fit.
    """
    user = re.sub(r"[^a-z0-9]", "", user_name.lower())
    base = f"img{identity}"
    return f"{base}{user[: _STORAGE_ACCOUNT_LIMIT - len(base)]}"


def _image_stem(path: Path) -> str:
    stem = _STEM.sub("-", path.stem.lower()).strip("-")
    if not stem:
        raise ValueError(f"{path.name} has no image name")
    return stem


def _check_vhd(path: Path) -> None:
    if path.suffix.lower() != ".vhd":
        raise ValueError(f"{path} is not a .vhd file")
    if not path.is_file():
        raise ValueError(f"{path} is not a file")
    if path.stat().st_size % 512 != 0:
        raise ValueError(f"{path} is not a page blob: its size is not a multiple of 512 bytes")

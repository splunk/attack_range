from pathlib import Path
from uuid import UUID

import pytest

from attack_range.application.images import ImageUpload, ImageUploadError
from attack_range.use_cases.upload_image import UploadImage, UploadImageInputDto, storage_account_name
from attack_range_infrastructure.azure_images import AzureCliImageUploader
from cli.main import main

IDENTITY = UUID("e6fffcb8-0000-4000-8000-000000000001")
IMAGE_ID = (
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/"
    "images-e6fffcb8-tester/providers/Microsoft.Compute/images/"
    "cisco-secure-firewall-threat-defense-virtual-7-6-6-115-e6fffcb8-tester"
)


class Presenter:
    def __init__(self) -> None:
        self.presented = None

    def present(self, output_dto) -> None:
        self.presented = output_dto


def vhd(tmp_path: Path, name: str = "Cisco_Secure_Firewall_Threat_Defense_Virtual-7.6.6-115.vhd") -> Path:
    path = tmp_path / name
    path.write_bytes(b"\0" * 512)
    return path


def test_upload_names_follow_the_cloud_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("attack_range.use_cases.upload_image.uuid4", lambda: IDENTITY)
    captured: list[ImageUpload] = []

    class Uploader:
        def upload(self, image: ImageUpload) -> str:
            captured.append(image)
            return IMAGE_ID

    presenter = Presenter()
    UploadImage(presenter, Uploader()).execute(UploadImageInputDto(vhd(tmp_path), "westeurope", "tester"))

    image = captured[0]
    assert image.resource_group == "images-e6fffcb8-tester"
    assert image.storage_account == "imge6fffcb8tester"
    assert image.container == "vhds-e6fffcb8-tester"
    assert image.blob_name == "Cisco_Secure_Firewall_Threat_Defense_Virtual-7.6.6-115.vhd"
    assert image.image_name == "cisco-secure-firewall-threat-defense-virtual-7-6-6-115-e6fffcb8-tester"
    assert image.os_type == "Linux"
    assert image.hyper_v_generation == "V1"
    assert presenter.presented is not None and presenter.presented.image_id == IMAGE_ID


def test_storage_account_name_keeps_the_identity_and_only_letters_and_digits() -> None:
    name = storage_account_name("e6fffcb8", "a-very-long-user-name-that-will-not-fit")

    assert name == "imge6fffcb8averylonguser"
    assert len(name) == 24
    assert name.isalnum()


def test_upload_rejects_a_vhd_whose_size_is_not_a_page(tmp_path: Path) -> None:
    path = tmp_path / "disk.vhd"
    path.write_bytes(b"\0" * 100)
    presenter = Presenter()

    UploadImage(presenter, lambda image: "").execute(UploadImageInputDto(path, "westeurope", "tester"))

    assert presenter.presented is not None
    assert presenter.presented.success is False
    assert "512" in (presenter.presented.error or "")


def test_azure_cli_uploads_a_page_blob_and_creates_the_image(tmp_path: Path) -> None:
    calls: list[tuple[list[str], bool]] = []

    def run(args: list[str], stream: bool) -> str:
        calls.append((args, stream))
        if args[1:3] == ["image", "create"]:
            return IMAGE_ID + "\n"
        return ""

    image = ImageUpload(
        vhd=vhd(tmp_path),
        region="westeurope",
        os_type="Linux",
        hyper_v_generation="V1",
        resource_group="images-e6fffcb8-tester",
        storage_account="imge6fffcb8tester",
        container="vhds-e6fffcb8-tester",
        blob_name="disk.vhd",
        image_name="disk-e6fffcb8-tester",
    )

    assert AzureCliImageUploader(run).upload(image) == IMAGE_ID
    commands = [" ".join(args[:4]) for args, _stream in calls]
    assert commands == [
        "az group create --name",
        "az storage account create",
        "az storage container create",
        "az storage blob upload",
        "az image create --resource-group",
    ]
    upload = calls[3][0]
    assert upload[upload.index("--type") + 1] == "page"
    assert upload[upload.index("--auth-mode") + 1] == "key"
    assert calls[3][1] is True
    source = calls[4][0][calls[4][0].index("--source") + 1]
    assert source == "https://imge6fffcb8tester.blob.core.windows.net/vhds-e6fffcb8-tester/disk.vhd"


def test_azure_cli_reports_a_missing_image_id(tmp_path: Path) -> None:
    image = ImageUpload(
        vhd=vhd(tmp_path),
        region="westeurope",
        os_type="Linux",
        hyper_v_generation="V1",
        resource_group="images-e6fffcb8-tester",
        storage_account="imge6fffcb8tester",
        container="vhds-e6fffcb8-tester",
        blob_name="disk.vhd",
        image_name="disk-e6fffcb8-tester",
    )

    with pytest.raises(ImageUploadError, match="did not return an image id"):
        AzureCliImageUploader(lambda args, stream: "").upload(image)


def test_cli_upload_azure_prints_the_image_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("attack_range.use_cases.upload_image.uuid4", lambda: IDENTITY)

    def upload(self, image: ImageUpload) -> str:
        return IMAGE_ID

    monkeypatch.setattr("attack_range_infrastructure.azure_images.AzureCliImageUploader.upload", upload)
    path = vhd(tmp_path)

    with pytest.raises(SystemExit) as raised:
        main(["upload", "azure", str(path), "--region", "westeurope"])

    assert raised.value.code == 0
    output = capsys.readouterr().out
    assert IMAGE_ID in output
    assert "images-e6fffcb8-tester" in output

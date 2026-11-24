from pathlib import Path

from attack_range.use_cases.upload_image import HyperVGeneration, OsType, UploadImageInputDto
from attack_range_infrastructure.storage import UserConfigError
from cli.actions.common import open_container
from cli.actions.provision import _user_name


def upload_azure_action(path: Path, region: str, os_type: OsType, generation: HyperVGeneration) -> int:
    """Upload a VHD and create an Azure managed image. Return the exit code."""
    container = open_container()
    try:
        user_name = _user_name(container)
    except UserConfigError as error:
        print(error)
        return 2
    container.upload_factory().execute(UploadImageInputDto(
        path=path,
        region=region,
        user_name=user_name,
        os_type=os_type,
        hyper_v_generation=generation,
    ))
    presented = container.upload_output_boundary().presented
    return 0 if presented is not None and presented.success else 1

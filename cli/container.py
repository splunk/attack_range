from pathlib import Path
from typing import Optional

from dependency_injector import containers, providers

from attack_range.use_cases.build import Build
from attack_range.use_cases.destroy import Destroy
from attack_range.use_cases.get_range import GetRange
from attack_range.use_cases.list_ranges import ListRanges
from attack_range.use_cases.plan import Plan
from attack_range.use_cases.prune_ranges import PruneRanges
from attack_range.use_cases.update import Update
from attack_range.use_cases.upload_image import UploadImage
from attack_range_infrastructure.azure_images import AzureCliImageUploader
from attack_range_infrastructure.guests import AnsibleGuestProvisioner
from attack_range_infrastructure.storage import (
    AttackRangeHome,
    FileCyberRangeRepository,
    FileRangeDocuments,
    YamlRangeStore,
)
from attack_range_infrastructure.terraform import TerraformProvisioner
from cli.operator import CliOperator
from cli.presenter import (
    CliGetPresenter,
    CliListPresenter,
    CliProvisionLog,
    CliProvisionPresenter,
    CliPrunePresenter,
    CliUploadPresenter,
)


def _home(root: Optional[Path]) -> AttackRangeHome:
    """The home folder, created on first use."""
    return AttackRangeHome(root).ensure()


class Container(containers.DeclarativeContainer):
    """Wire the use cases to the home folder, Terraform, and the CLI presenters."""

    config = providers.Configuration()

    home = providers.Singleton(_home, root=config.home)
    repository = providers.Factory(FileCyberRangeRepository, home=home)
    range_store = providers.Singleton(YamlRangeStore, home=home)
    range_documents = providers.Factory(FileRangeDocuments, home=home, repository=repository)
    log = providers.Singleton(CliProvisionLog)
    provisioner = providers.Factory(
        TerraformProvisioner,
        home=home,
        terraform_bin=config.terraform_bin,
        log=log,
    )
    operator = providers.Singleton(CliOperator)
    guests = providers.Factory(AnsibleGuestProvisioner, home=home, log=log, operator=operator)
    output_boundary = providers.Singleton(CliProvisionPresenter)
    list_output_boundary = providers.Singleton(CliListPresenter)

    plan_factory = providers.Factory(
        Plan,
        output_boundary=output_boundary,
        repository=repository,
        provisioner=provisioner,
    )
    build_factory = providers.Factory(
        Build,
        output_boundary=output_boundary,
        repository=repository,
        documents=range_documents,
        store=range_store,
        provisioner=provisioner,
        guests=guests,
        operator=operator,
    )
    update_factory = providers.Factory(
        Update,
        output_boundary=output_boundary,
        repository=repository,
        documents=range_documents,
        store=range_store,
        provisioner=provisioner,
        guests=guests,
        operator=operator,
    )
    destroy_factory = providers.Factory(
        Destroy,
        output_boundary=output_boundary,
        documents=range_documents,
        store=range_store,
        provisioner=provisioner,
    )
    list_factory = providers.Factory(
        ListRanges,
        output_boundary=list_output_boundary,
        store=range_store,
    )
    get_output_boundary = providers.Singleton(CliGetPresenter)
    get_factory = providers.Factory(
        GetRange,
        output_boundary=get_output_boundary,
        documents=range_documents,
        store=range_store,
    )
    upload_output_boundary = providers.Singleton(CliUploadPresenter)
    image_uploader = providers.Factory(AzureCliImageUploader, log=log)
    upload_factory = providers.Factory(
        UploadImage,
        output_boundary=upload_output_boundary,
        uploader=image_uploader,
    )
    prune_output_boundary = providers.Singleton(CliPrunePresenter)
    prune_factory = providers.Factory(
        PruneRanges,
        output_boundary=prune_output_boundary,
        store=range_store,
        documents=range_documents,
    )

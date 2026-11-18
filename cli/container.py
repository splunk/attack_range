from pathlib import Path
from typing import Optional

from dependency_injector import containers, providers

from attack_range.use_cases.build import Build
from attack_range.use_cases.destroy import Destroy
from attack_range.use_cases.list_ranges import ListRanges
from attack_range.use_cases.plan import Plan
from attack_range_infrastructure.storage import (
    AttackRangeHome,
    FileCyberRangeRepository,
    FileRangeDocuments,
    YamlRangeStore,
)
from attack_range_infrastructure.terraform import TerraformProvisioner
from cli.presenter import CliListPresenter, CliProvisionLog, CliProvisionPresenter


def _home(root: Optional[Path]) -> AttackRangeHome:
    """The home folder, created on first use."""
    return AttackRangeHome(root).ensure()


class Container(containers.DeclarativeContainer):
    """Wire the use cases to the home folder, Terraform, and the CLI presenters."""

    config = providers.Configuration()

    home = providers.Singleton(_home, root=config.home)
    repository = providers.Factory(FileCyberRangeRepository)
    range_store = providers.Singleton(YamlRangeStore, home=home)
    range_documents = providers.Factory(FileRangeDocuments, home=home, repository=repository)
    log = providers.Singleton(CliProvisionLog)
    provisioner = providers.Factory(
        TerraformProvisioner,
        home=home,
        terraform_bin=config.terraform_bin,
        log=log,
    )
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

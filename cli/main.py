import argparse
import sys
from pathlib import Path
from typing import get_args
from uuid import UUID

import yaml

from attack_range.application.overrides import DeployOverrides, FieldOverride
from attack_range.domain.entities.common import Provider
from cli.actions.get import get_action
from cli.actions.init import init_action
from cli.actions.list import list_action
from cli.actions.upload import upload_azure_action
from cli.actions.provision import (
    build_action,
    destroy_action,
    plan_action,
    update_action,
    update_change_action,
    update_remove_action,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="attack-range",
        description="Build cyber ranges from YAML templates. Ranges are kept in ~/.attack_range "
        "(or $ATTACK_RANGE_HOME).",
    )
    actions = parser.add_subparsers(dest="action", required=True)

    plan = actions.add_parser("plan", help="Show what build would create, without registering anything")
    _template_arguments(plan)
    _override_arguments(plan)
    _terraform_argument(plan)

    build = actions.add_parser("build", help="Register a template as a new cyber range and create it")
    _template_arguments(build)
    _override_arguments(build)
    build.add_argument(
        "--local-state",
        action="store_true",
        help="Keep Terraform state in the range folder instead of S3 or Azure Blob Storage",
    )
    _terraform_argument(build)

    update = actions.add_parser("update", help="Add, change, or remove config in a cyber range")
    update_commands = update.add_subparsers(dest="update_action", required=True)
    add = update_commands.add_parser("add", help="Merge new or changed documents and apply them")
    add.add_argument("range_id", type=UUID, metavar="RANGE_ID", help="Id of the range, as shown by list")
    add.add_argument(
        "location",
        type=Path,
        metavar="PATH",
        help="A .yaml file, or a directory of them, to merge into the range",
    )
    _override_arguments(add)
    _terraform_argument(add)
    change = update_commands.add_parser("change", help="Apply a modified file or folder of existing documents")
    change.add_argument("range_id", type=UUID, metavar="RANGE_ID", help="Id of the range, as shown by list")
    change.add_argument(
        "location",
        type=Path,
        metavar="PATH",
        help="A modified .yaml file, or a directory of them, already in the range",
    )
    _terraform_argument(change)
    remove = update_commands.add_parser("remove", help="Remove config files and apply the result")
    remove.add_argument("range_id", type=UUID, metavar="RANGE_ID", help="Id of the range, as shown by list")
    remove.add_argument(
        "files",
        type=_config_files,
        metavar="FILES",
        help="Comma-separated config file names, as shown by get",
    )
    _terraform_argument(remove)

    destroy = actions.add_parser("destroy", help="Remove all infrastructure of a cyber range")
    destroy.add_argument("range_id", type=UUID, metavar="RANGE_ID", help="Id of the range, as shown by list")
    destroy.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Destroy without asking for confirmation",
    )
    _terraform_argument(destroy)

    list_parser = actions.add_parser("list", help="Show the cyber ranges and their state")
    list_parser.add_argument("--all", action="store_true", help="Include destroyed ranges")

    get = actions.add_parser("get", help="Show one cyber range")
    get.add_argument("range_id", type=UUID, metavar="RANGE_ID", help="Id of the range, as shown by list")

    actions.add_parser(
        "init",
        help="Set or replace the stored user name and password. Refused while a range is built",
    )

    upload = actions.add_parser("upload", help="Publish a local disk image to a cloud provider")
    upload_commands = upload.add_subparsers(dest="upload_action", required=True)
    azure = upload_commands.add_parser("azure", help="Upload a VHD and create a managed image")
    azure.add_argument("vhd", type=Path, metavar="VHD", help="Path to a .vhd file")
    azure.add_argument("--region", required=True, help="Azure region for the image, for example westeurope")
    azure.add_argument("--os-type", choices=("Linux", "Windows"), default="Linux", help="Operating system of the VHD")
    azure.add_argument(
        "--generation",
        choices=("V1", "V2"),
        default="V1",
        help="Hyper-V generation of the VHD",
    )

    args = parser.parse_args(argv)
    if args.action == "plan":
        sys.exit(plan_action(args.location, args.provider, args.terraform, _overrides(args)))
    if args.action == "build":
        sys.exit(build_action(args.location, args.provider, args.local_state, args.terraform, _overrides(args)))
    if args.action == "update" and args.update_action == "add":
        sys.exit(update_action(args.range_id, args.location, args.terraform, _overrides(args)))
    if args.action == "update" and args.update_action == "change":
        sys.exit(update_change_action(args.range_id, args.location, args.terraform))
    if args.action == "update":
        sys.exit(update_remove_action(args.range_id, args.files, args.terraform))
    if args.action == "destroy":
        if not args.yes and not sys.stdin.isatty():
            parser.error("destroy needs --yes when it does not run in a terminal")
        sys.exit(destroy_action(args.range_id, args.terraform, None if args.yes else _confirm_destroy))
    if args.action == "get":
        sys.exit(get_action(args.range_id))
    if args.action == "init":
        sys.exit(init_action())
    if args.action == "upload":
        sys.exit(upload_azure_action(args.vhd, args.region, args.os_type, args.generation))
    sys.exit(list_action(args.all))


def _template_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "location",
        type=Path,
        metavar="PATH",
        help="A cyber range .yaml file, or a directory of them",
    )
    parser.add_argument(
        "--provider",
        choices=get_args(Provider),
        help="Provider whose bindings to use. Required when the documents bind more than one",
    )


def _override_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--set",
        action="append",
        type=_set,
        metavar="NAME.PATH=VALUE",
        help="Replace a document field. NAME is the document name, or * for every document of this "
        "provider that has the field. PATH is the field, such as spec.location or spec.azure.imageId. "
        "VALUE is YAML, so a list is written [198.51.100.4/32, 203.0.113.8/32]",
    )


def _overrides(args: argparse.Namespace) -> DeployOverrides:
    return DeployOverrides(sets=tuple(args.set or ()))


def _set(value: str) -> FieldOverride:
    target, separator, raw = value.partition("=")
    path = tuple(target.split("."))
    if not separator or len(path) < 2 or any(not part for part in path):
        raise argparse.ArgumentTypeError("expected NAME.PATH=VALUE")
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise argparse.ArgumentTypeError(str(error)) from error
    return FieldOverride(path[0], path[1:], parsed)


def _config_files(value: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in value.split(","))
    if not names or any(not name for name in names):
        raise argparse.ArgumentTypeError("expected a comma-separated list of config file names")
    return names


def _terraform_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--terraform",
        default="terraform",
        help="Terraform binary (default: terraform)",
    )


def _confirm_destroy(description: str) -> bool:
    answer = input(f"Destroy all infrastructure of {description}? Type 'yes' to continue: ")
    if answer.strip() == "yes":
        return True
    print("Destroy cancelled.", file=sys.stderr)
    return False

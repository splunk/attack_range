import argparse
import sys
from pathlib import Path
from typing import get_args
from uuid import UUID

from attack_range.domain.entities.common import Provider
from cli.actions.list import list_action
from cli.actions.provision import build_action, destroy_action, plan_action


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="attack-range",
        description="Build cyber ranges from YAML templates. Ranges are kept in ~/.attack_range "
        "(or $ATTACK_RANGE_HOME).",
    )
    actions = parser.add_subparsers(dest="action", required=True)

    plan = actions.add_parser("plan", help="Show what build would create, without registering anything")
    _template_arguments(plan)
    _terraform_argument(plan)

    build = actions.add_parser("build", help="Register a template as a new cyber range and create it")
    _template_arguments(build)
    build.add_argument(
        "--local-state",
        action="store_true",
        help="Keep Terraform state in the range folder instead of S3 or Azure Blob Storage",
    )
    _terraform_argument(build)

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

    args = parser.parse_args(argv)
    if args.action == "plan":
        sys.exit(plan_action(args.location, args.provider, args.terraform))
    if args.action == "build":
        sys.exit(build_action(args.location, args.provider, args.local_state, args.terraform))
    if args.action == "destroy":
        if not args.yes and not sys.stdin.isatty():
            parser.error("destroy needs --yes when it does not run in a terminal")
        sys.exit(destroy_action(args.range_id, args.terraform, None if args.yes else _confirm_destroy))
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

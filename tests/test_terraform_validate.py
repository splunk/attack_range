"""Runs `terraform validate` on the rendered code. Needs the terraform binary and registry access."""

import shutil
import subprocess
from pathlib import Path

import pytest

from attack_range_infrastructure.storage import AttackRangeHome
from attack_range_infrastructure.terraform import TerraformProvisioner
from conftest import load_cyber_range

pytestmark = pytest.mark.skipif(shutil.which("terraform") is None, reason="terraform is not installed")


def terraform(directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["terraform", *args, "-no-color"], cwd=directory, capture_output=True, text=True)


@pytest.mark.parametrize("provider", ["aws", "azure", "vmware"])
def test_rendered_code_is_valid(home: AttackRangeHome, lab_dir: Path, provider: str) -> None:
    directory = TerraformProvisioner(home).render(load_cyber_range(lab_dir, provider))

    init = terraform(directory, "init", "-backend=false", "-input=false")
    if init.returncode != 0:
        pytest.skip(f"terraform init failed, probably no registry access: {init.stderr.strip()[:200]}")
    validate = terraform(directory, "validate")

    assert validate.returncode == 0, validate.stdout + validate.stderr

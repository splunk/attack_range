import dataclasses
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest

from attack_range.application.provisioner import ProvisionLog, Provisioner, ProvisionerError
from attack_range_infrastructure.storage import AttackRangeHome
from attack_range_infrastructure.terraform import LocalBackend, TerraformBackend, TerraformProvisioner
from attack_range_infrastructure.terraform.provisioner import CONFIG_FILE, PLAN_FILE
from conftest import edit, load_cyber_range, registered


class FakeBackend(TerraformBackend):
    type = "s3"

    def __init__(self) -> None:
        super().__init__("test")
        self.ensured: list[str] = []

    def ensure(self, cyber_range) -> None:
        self.ensured.append(cyber_range.name)

    def config(self, cyber_range) -> dict[str, str]:
        return {"bucket": "state", "key": self.state_key(cyber_range)}


class RecordingProvisioner(TerraformProvisioner):
    """Records terraform calls instead of running them."""

    def __init__(
        self, home: AttackRangeHome, fail_on: str = "", backend: Optional[TerraformBackend] = None
    ) -> None:
        super().__init__(home, backends={"aws": backend or LocalBackend()})
        self.calls: list[list[str]] = []
        self.fail_on = fail_on

    def _run(self, args: list[str], directory: Path, stream: bool = True) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[0] == "plan":
            (directory / PLAN_FILE).write_text("plan")
        stdout = json.dumps({"vpc_id": {"value": "vpc-1"}}) if args[0] == "output" else f"{args[0]} ok\n"
        return subprocess.CompletedProcess(args, 1 if args[0] == self.fail_on else 0, stdout, "")


@pytest.fixture
def template(ar_template_dir: Path):
    return load_cyber_range(ar_template_dir, "aws")


@pytest.fixture
def cyber_range(template):
    return registered(template)


def test_is_a_provisioner(home: AttackRangeHome) -> None:
    assert isinstance(TerraformProvisioner(home), Provisioner)


def test_registered_range_is_rendered_in_its_folder(home: AttackRangeHome, cyber_range) -> None:
    directory = TerraformProvisioner(home).render(cyber_range)

    assert directory == home.ranges_dir / str(cyber_range.id) / "terraform"
    document = json.loads((directory / CONFIG_FILE).read_text())
    assert "aws_vpc" in document["resource"]
    assert document["terraform"]["backend"] == {"s3": {}}


def test_template_is_planned_with_local_state(home: AttackRangeHome, template) -> None:
    backend = FakeBackend()
    provisioner = RecordingProvisioner(home, backend=backend)

    provisioner.plan(template)

    directory = home.plans_dir / "ar-aws"
    assert "backend" not in json.loads((directory / CONFIG_FILE).read_text())["terraform"]
    assert backend.ensured == []
    assert provisioner.calls[0] == ["init", "-input=false", "-no-color"]


def test_local_state_range_keeps_state_locally(home: AttackRangeHome, template) -> None:
    directory = TerraformProvisioner(home).render(registered(template, local_state=True))

    assert "backend" not in json.loads((directory / CONFIG_FILE).read_text())["terraform"]


def test_vmware_keeps_local_state(home: AttackRangeHome, lab_dir: Path) -> None:
    directory = TerraformProvisioner(home).render(registered(load_cyber_range(lab_dir, "vmware")))

    assert "backend" not in json.loads((directory / CONFIG_FILE).read_text())["terraform"]


def test_init_prepares_backend_and_passes_config(home: AttackRangeHome, cyber_range) -> None:
    backend = FakeBackend()
    provisioner = RecordingProvisioner(home, backend=backend)

    provisioner.plan(cyber_range)

    assert backend.ensured == ["ar"]
    assert provisioner.calls[0] == [
        "init", "-input=false", "-no-color", "-migrate-state", "-force-copy",
        "-backend-config=bucket=state", f"-backend-config=key=test/{cyber_range.id}/terraform.tfstate",
    ]


def test_backend_failure_raises(home: AttackRangeHome, cyber_range) -> None:
    class BrokenBackend(FakeBackend):
        def ensure(self, cyber_range) -> None:
            raise RuntimeError("no credentials")

    with pytest.raises(ProvisionerError, match="s3 state backend: no credentials"):
        RecordingProvisioner(home, backend=BrokenBackend()).plan(cyber_range)


@pytest.mark.parametrize("action", ["apply", "destroy", "clean"])
def test_template_cannot_be_changed(home: AttackRangeHome, template, action: str) -> None:
    provisioner = RecordingProvisioner(home)

    with pytest.raises(ProvisionerError, match="only registered ranges"):
        getattr(provisioner, action)(template)
    assert provisioner.calls == []


def test_plan_then_apply_uses_saved_plan(home: AttackRangeHome, cyber_range) -> None:
    provisioner = RecordingProvisioner(home)

    planned = provisioner.plan(cyber_range)
    applied = provisioner.apply(cyber_range)

    assert planned.success and applied.success
    assert [call[0] for call in provisioner.calls] == ["init", "plan", "init", "apply", "output"]
    assert provisioner.calls[1][-1] == f"-out={PLAN_FILE}"
    assert provisioner.calls[3][-1] == PLAN_FILE
    assert applied.outputs == {"vpc_id": "vpc-1"}
    assert not (home.terraform_dir(cyber_range.id) / PLAN_FILE).exists()


def test_apply_without_plan(home: AttackRangeHome, cyber_range) -> None:
    provisioner = RecordingProvisioner(home)

    provisioner.apply(cyber_range)

    assert provisioner.calls[1] == ["apply", "-input=false", "-no-color", "-auto-approve"]


def test_changed_config_discards_saved_plan(home: AttackRangeHome, tmp_path: Path, ar_template_dir: Path) -> None:
    source = tmp_path / "range"
    shutil.copytree(ar_template_dir, source)
    provisioner = RecordingProvisioner(home)
    cyber_range = registered(load_cyber_range(source, "aws"))
    provisioner.plan(cyber_range)

    binding = source / "win.server-binding.aws.yaml"
    binding.write_text(binding.read_text().replace("t3.large", "t3.xlarge"))
    provisioner.apply(dataclasses.replace(load_cyber_range(source, "aws"), id=cyber_range.id))

    assert provisioner.calls[3][-1] != PLAN_FILE


def test_destroy(home: AttackRangeHome, cyber_range) -> None:
    provisioner = RecordingProvisioner(home)

    result = provisioner.destroy(cyber_range)

    assert result.success
    assert provisioner.calls[1] == ["destroy", "-input=false", "-no-color", "-auto-approve"]


def test_clean_removes_generated_code(home: AttackRangeHome, cyber_range) -> None:
    provisioner = RecordingProvisioner(home)
    directory = provisioner.render(cyber_range)

    provisioner.clean(cyber_range)

    assert not directory.exists()
    assert directory.parent.is_dir()


def test_failed_init_stops(home: AttackRangeHome, cyber_range) -> None:
    provisioner = RecordingProvisioner(home, fail_on="init")

    result = provisioner.plan(cyber_range)

    assert not result.success
    assert provisioner.calls == [["init", "-input=false", "-no-color"]]


def test_render_error_becomes_provisioner_error(home: AttackRangeHome, lab_dir: Path) -> None:
    edit(lab_dir / "lab.server.yaml", "address: 10.0.1.10", "address: 10.0.1.10\n      public: true")

    with pytest.raises(ProvisionerError, match="has no internet gateway"):
        TerraformProvisioner(home).render(load_cyber_range(lab_dir, "aws"))


class RecordingLog(ProvisionLog):
    def __init__(self) -> None:
        self.lines: list[str] = []

    def line(self, text: str) -> None:
        self.lines.append(text)


def test_streams_terraform_output_to_log(home: AttackRangeHome, tmp_path: Path, template) -> None:
    terraform = tmp_path / "terraform"
    terraform.write_text('#!/bin/sh\necho "running $1"\necho "warning on stderr" >&2\n')
    terraform.chmod(0o755)
    log = RecordingLog()
    provisioner = TerraformProvisioner(home, terraform_bin=str(terraform), log=log)

    result = provisioner.plan(template)

    assert result.success
    assert log.lines == ["running init", "warning on stderr", "running plan", "warning on stderr"]
    assert "running plan" in result.output

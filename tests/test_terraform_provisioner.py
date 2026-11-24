import dataclasses
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

import pytest
import yaml

from attack_range.application.provisioner import ProvisionLog, Provisioner, ProvisionerError
from attack_range_infrastructure.guests import AnsibleGuestProvisioner
from attack_range_infrastructure.keys import RangeKeyPair
from attack_range_infrastructure.storage import AttackRangeHome
from attack_range_infrastructure.storage.file_cyber_range_repository import FileCyberRangeRepository
from attack_range_infrastructure.terraform import LocalBackend, TerraformBackend, TerraformProvisioner
from attack_range_infrastructure.terraform.provisioner import CONFIG_FILE, PLAN_FILE
from conftest import REPO, edit, load_cyber_range, registered


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


def test_aws_range_keeps_its_key_and_destroy_removes_the_aws_pair(home: AttackRangeHome, cyber_range) -> None:
    provisioner = RecordingProvisioner(home)

    provisioner.render(cyber_range)
    private = home.keys_dir(cyber_range.id) / "id_rsa"
    public = home.keys_dir(cyber_range.id) / "id_rsa.pub"
    assert private.stat().st_mode & 0o777 == 0o600
    first = public.read_text()
    rendered = json.loads((home.terraform_dir(cyber_range.id) / CONFIG_FILE).read_text())
    assert rendered["resource"]["aws_key_pair"]["range"]["public_key"] == first.strip()
    assert "OPENSSH PRIVATE KEY" not in (home.terraform_dir(cyber_range.id) / CONFIG_FILE).read_text()
    for instance in rendered["resource"]["aws_instance"].values():
        assert instance["key_name"] == "${aws_key_pair.range.key_name}"

    provisioner.render(cyber_range)
    assert public.read_text() == first

    provisioner.destroy(cyber_range)
    destroyed = json.loads((home.terraform_dir(cyber_range.id) / CONFIG_FILE).read_text())
    assert destroyed["resource"]["aws_key_pair"]["range"]["public_key"] == first.strip()
    assert provisioner.calls[-1][0] == "destroy"


def test_gateway_provisioning_saves_the_client_config(home: AttackRangeHome, lab_dir: Path) -> None:
    cyber_range = registered(load_cyber_range(lab_dir, "aws"))
    RangeKeyPair(home.keys_dir(cyber_range.id)).ensure()

    class Fetching(AnsibleGuestProvisioner):
        def _ansible(self, directory: Path, action: str, *, retry: bool) -> None:
            assert "attack_range.wireguard" in (directory / "provision.yml").read_text()
            if action == "get_config":
                fetched = directory / "client_configs"
                fetched.mkdir()
                (fetched / "client1.conf").write_text("[Peer]\nEndpoint = REPLACE_ENDPOINT:51820\n")

    config = Fetching(home).provision_gateway(cyber_range, "203.0.113.10")

    assert "Endpoint = 203.0.113.10:51820" in config.text
    assert config.path == home.wireguard_config(cyber_range.id)
    assert config.path.read_text() == config.text


def test_server_provisioning_runs_the_declared_roles(home: AttackRangeHome, ar_template_dir: Path) -> None:
    cyber_range = registered(load_cyber_range(ar_template_dir, "aws"))
    RangeKeyPair(home.keys_dir(cyber_range.id)).ensure()
    calls: list[list[str]] = []

    class Recording(AnsibleGuestProvisioner):
        def _run(
            self, directory: Path, command: list[str], title: str, log: Optional[ProvisionLog] = None
        ) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")

    Recording(home).provision_servers(cyber_range, {"splunk": "10.0.2.10"})

    play = (home.range_dir(cyber_range.id) / "ansible" / "provision.yml").read_text()
    assert "P4T12ICK.ludus_ar_splunk" in play
    assert "P4T12ICK.ar_guacamole" in play
    assert calls[0][:3] == ["ansible-galaxy", "install", "P4T12ICK.ludus_ar_splunk"]
    assert calls[-1][:3] == ["ansible-playbook", "-i", "inventory.yml"]


def test_missing_gnu_tar_stops_before_the_play(home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch) -> None:
    source = REPO / "templates" / "aws" / "ar_splunk_windows"
    cyber_range = registered(FileCyberRangeRepository(home).load(source, "aws"))
    RangeKeyPair(home.keys_dir(cyber_range.id)).ensure()
    monkeypatch.setattr("attack_range_infrastructure.guests._gnu_tar", lambda environment: None)
    calls: list[list[str]] = []

    class Recording(AnsibleGuestProvisioner):
        def _run(
            self, directory: Path, command: list[str], title: str, log: Optional[ProvisionLog] = None
        ) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(ProvisionerError, match="GNU tar"):
        Recording(home).provision_servers(cyber_range, {"splunk": "10.0.2.10"})

    assert calls == []


def test_splunk_search_head_uses_the_official_role(home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch) -> None:
    source = REPO / "templates" / "aws" / "ar_splunk_windows"
    cyber_range = registered(FileCyberRangeRepository(home).load(source, "aws"))
    RangeKeyPair(home.keys_dir(cyber_range.id)).ensure()
    monkeypatch.setattr("attack_range_infrastructure.guests._gnu_tar", lambda environment: Path("/usr/bin/tar"))
    calls: list[list[str]] = []

    class Recording(AnsibleGuestProvisioner):
        def _run(
            self, directory: Path, command: list[str], title: str, log: Optional[ProvisionLog] = None
        ) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if command[0] == "git":
                checkout = Path(command[-1])
                tasks = checkout / "roles" / "splunk" / "tasks"
                tasks.mkdir(parents=True)
                (tasks / "main.yml").write_text("---\n")
            return subprocess.CompletedProcess(command, 0, "", "")

    Recording(home).provision_servers(cyber_range, {"splunk": "10.0.2.10"})

    ansible = home.range_dir(cyber_range.id) / "ansible"
    assert calls[0][:3] == ["ansible-galaxy", "collection", "install"]
    assert calls[0][3:6] == ["ansible.posix", "community.general", "amazon.aws"]
    clone = calls[1]
    assert clone[:4] == ["git", "clone", "--depth", "1"]
    assert clone[4:6] == ["--branch", "v2.2.0"]
    assert clone[6] == "https://github.com/splunk/ansible-role-for-splunk"
    assert (ansible / "roles" / "splunk").resolve() == (Path(clone[-1]) / "roles" / "splunk").resolve()
    inventory = yaml.safe_load((ansible / "inventory.yml").read_text())
    assert inventory["all"]["children"]["full"]["hosts"] == {"splunk": {}}
    assert inventory["all"]["children"]["search"]["hosts"] == {"splunk": {}}
    assert inventory["all"]["hosts"]["splunk"]["ansible_python_interpreter"] == "/usr/bin/python3"
    assert inventory["all"]["hosts"]["splunk"]["ansible_become"] is True
    play = yaml.safe_load((ansible / "provision.yml").read_text())
    assert "become" not in play[0]
    app_step = cyber_range.servers[0].spec.provisioning[1]
    assert str(app_step.repository) == "https://github.com/splunk/ansible-role-for-splunk"
    assert app_step.revision == "v2.2.0"
    assert app_step.role_path == "roles/splunk"
    install, apps = play[0]["roles"]
    assert install["role"] == "splunk"
    assert install["deployment_task"] == "check_splunk.yml"
    assert install["splunk_admin_password"] == "Test123!"
    assert install["splunk_package_version"] == "10.6.2.5"
    assert install["build_id"] == "b07ce3b48d58"
    assert install["splunk_download_local"] is False
    assert apps["deployment_task"] == "configure_apps.yml"
    assert apps["splunk_app_s3_bucket"] == "attack-range-appbinaries"
    assert apps["environment"] == {"AWS_DEFAULT_REGION": "us-west-2"}
    assert [item["s3_object"] for item in apps["apps"]] == [
        "splunk-add-on-for-microsoft-windows_901.tgz",
        "splunk-add-on-for-sysmon-for-linux_100.tgz",
        "splunk-add-on-for-sysmon_402.tgz",
        "splunk-add-on-for-unix-and-linux_1000.tgz",
        "splunk-common-information-model-(cim)_602.tgz",
        "DA-ESS-ContentUpdate-latest.tar.gz",
        "cisco-security-cloud_372.tgz",
    ]


def test_servers_are_provisioned_together(home: AttackRangeHome, ar_template_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cyber_range = registered(load_cyber_range(ar_template_dir, "aws"))
    splunk = cyber_range.servers[0]
    app = splunk.model_copy(deep=True, update={"metadata": splunk.metadata.model_copy(update={"name": "app"})})
    cyber_range = dataclasses.replace(cyber_range, servers=[splunk, app])
    RangeKeyPair(home.keys_dir(cyber_range.id)).ensure()
    monkeypatch.setattr("attack_range_infrastructure.guests.ATTEMPTS", 1)
    calls: list[list[str]] = []
    started: list[float] = []

    class Recording(AnsibleGuestProvisioner):
        def _run(self, directory: Path, command: list[str], title: str, log: Optional[ProvisionLog] = None) -> subprocess.CompletedProcess[str]:
            if command[0] == "ansible-playbook":
                started.append(time.monotonic())
                failed = "--limit" in command and command[command.index("--limit") + 1] == "app"
                time.sleep(0.4)
                calls.append(command)
                return subprocess.CompletedProcess(command, 1 if failed else 0, "app failed" if failed else "", "")
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(ProvisionerError, match="ansible-playbook app failed"):
        Recording(home).provision_servers(cyber_range, {"splunk": "10.0.2.10", "app": "10.0.2.12"})

    limited = [command for command in calls if "--limit" in command]
    assert {command[command.index("--limit") + 1] for command in limited} == {"splunk", "app"}
    assert max(started) - min(started) < 0.2


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


def _vpc_name(directory: Path) -> str:
    document = json.loads((directory / CONFIG_FILE).read_text())
    return document["resource"]["aws_vpc"]["vpc"]["tags"]["Name"]


def test_plan_names_stay_stable_and_use_the_configured_user(home: AttackRangeHome, template) -> None:
    provisioner = TerraformProvisioner(home)

    first = _vpc_name(provisioner.render(template))
    second = _vpc_name(provisioner.render(template))

    assert first == second
    assert first.startswith("vpc-") and first.endswith("-tester")


def test_registered_names_keep_the_recorded_user(home: AttackRangeHome, template) -> None:
    home.config_file.write_text("user_name: other\n")
    cyber_range = dataclasses.replace(registered(template), user_name="ada")

    name = _vpc_name(TerraformProvisioner(home).render(cyber_range))

    prefix = str(cyber_range.id).split("-", 1)[0]
    assert name == f"vpc-{prefix}-ada"


def test_render_without_a_user_name_fails(home: AttackRangeHome, template) -> None:
    home.config_file.unlink()

    with pytest.raises(ProvisionerError, match="no user name"):
        TerraformProvisioner(home).render(template)


def test_streams_ansible_output_to_log(home: AttackRangeHome, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = tmp_path / "ansible-playbook"
    binary.write_text('#!/bin/sh\necho "PLAY wireguard"\n')
    binary.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    log = RecordingLog()
    directory = tmp_path / "play"
    directory.mkdir()

    AnsibleGuestProvisioner(home, log=log)._ansible(directory, "deploy", retry=False)

    assert log.lines == ["ansible-playbook wireguard deploy", "PLAY wireguard"]


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

import json
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from attack_range.domain.entities.range_record import RangeRecord
from attack_range.domain.value_objects.range_state import RangeState
from attack_range_infrastructure.storage import AttackRangeHome, YamlRangeStore
from attack_range_infrastructure.terraform import TerraformProvisioner
from cli.main import main


@pytest.fixture(autouse=True)
def piped_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make rich treat captured output as a pipe, whatever terminal runs the tests."""
    for variable in ("FORCE_COLOR", "TTY_COMPATIBLE", "TTY_INTERACTIVE", "COLUMNS"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")


@pytest.fixture
def terraform_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Replace the terraform CLI with a recorder that reports one server after apply."""
    calls: list[list[str]] = []

    def run(self, args: list[str], directory: Path, stream: bool = True) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        self.log.line(f"terraform {args[0]}")
        stdout = ""
        if args[0] == "output":
            stdout = json.dumps({"servers": {"value": {"win": {"private_ip": "10.0.2.11", "public_ip": None}}}})
        return subprocess.CompletedProcess(args, 0, stdout, "")

    monkeypatch.setattr(TerraformProvisioner, "_run", run)
    return calls


def run_cli(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as raised:
        main(argv)
    return raised.value.code


def build_range(location: Path, capsys: pytest.CaptureFixture[str], *args: str) -> UUID:
    assert run_cli(["build", str(location), "--local-state", *args]) == 0
    out = capsys.readouterr().out
    match = re.search(r"id\s+([0-9a-f-]{36})", out)
    assert match, out
    return UUID(match.group(1))


def record(home_root: Path, range_id: UUID) -> dict:
    return yaml.safe_load((home_root / "ranges" / str(range_id) / "range.yaml").read_text())


def test_first_run_creates_home(home_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["list"]) == 0

    assert (home_root / "ranges").is_dir() and (home_root / "plans").is_dir()
    assert "No cyber ranges" in capsys.readouterr().out


def test_plan_registers_nothing(
    home_root: Path, ar_template_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run_cli(["plan", str(ar_template_dir)])

    assert code == 0
    assert [call[0] for call in terraform_calls] == ["init", "plan"]
    assert terraform_calls[0] == ["init", "-input=false", "-no-color"]
    assert (home_root / "plans" / "ar-aws" / "main.tf.json").is_file()
    assert list((home_root / "ranges").iterdir()) == []
    out = capsys.readouterr().out
    assert "terraform plan" in out
    assert "ar on aws  planned" in out


def test_plan_applies_region_and_perimeter_overrides(
    home_root: Path, lab_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run_cli([
        "plan", str(lab_dir), "--provider", "aws",
        "--set", "*.spec.location=eu-west-2",
        "--set", "lab.spec.perimeter.sources=[198.51.100.4/32, 203.0.113.8/32]",
    ])

    assert code == 0
    rendered = (home_root / "plans" / "lab-aws" / "main.tf.json").read_text()
    assert "eu-west-2" in rendered
    assert "198.51.100.4/32" in rendered and "203.0.113.8/32" in rendered
    assert list((home_root / "ranges").iterdir()) == []
    assert "planned" in capsys.readouterr().out


def test_plan_rejects_a_perimeter_inside_the_address_space(
    home_root: Path, lab_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run_cli([
        "plan", str(lab_dir), "--provider", "aws",
        "--set", "lab.spec.perimeter.sources=[10.0.1.10/32]",
    ])

    assert code == 1
    assert "inside the address space" in capsys.readouterr().err
    assert terraform_calls == []
    assert list((home_root / "ranges").iterdir()) == []


def test_build_list_destroy(
    home_root: Path, ar_template_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    range_id = build_range(ar_template_dir, capsys)

    folder = home_root / "ranges" / str(range_id)
    assert sorted(path.name for path in (folder / "documents").glob("*.yaml")) == sorted(
        path.name for path in ar_template_dir.glob("*.yaml")
    )
    assert (folder / "terraform" / "main.tf.json").is_file()
    stored = record(home_root, range_id)
    assert stored["state"] == "built"
    assert stored["user_name"] == "tester"
    assert stored["local_state"] is True
    assert stored["outputs"]["servers"]["win"]["private_ip"] == "10.0.2.11"

    assert run_cli(["list"]) == 0
    listed = capsys.readouterr().out
    assert re.search(rf"{range_id}\s+ar\s+aws\s+eu-central-1\s+built\s", listed), listed

    terraform_calls.clear()
    assert run_cli(["destroy", str(range_id), "--yes"]) == 0
    assert "ar on aws  destroyed" in capsys.readouterr().out
    assert terraform_calls[0] == ["init", "-input=false", "-no-color"]
    assert terraform_calls[-1][0] == "destroy"
    assert record(home_root, range_id)["state"] == "destroyed"
    assert not (folder / "terraform").exists()
    assert (folder / "documents").is_dir()

    assert run_cli(["list"]) == 0
    listed = capsys.readouterr().out
    assert str(range_id) not in listed
    assert "1 destroyed range hidden" in listed
    assert run_cli(["list", "--all"]) == 0
    assert str(range_id) in capsys.readouterr().out


def test_old_destroyed_ranges_are_deleted(
    home_root: Path, ar_template_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    old, recent = build_range(ar_template_dir, capsys), build_range(ar_template_dir, capsys)
    for range_id in (old, recent):
        assert run_cli(["destroy", str(range_id), "--yes"]) == 0
    record_file = home_root / "ranges" / str(old) / "range.yaml"
    stored = yaml.safe_load(record_file.read_text())
    stored["updated_at"] = (datetime.now(UTC) - timedelta(days=31)).isoformat()
    record_file.write_text(yaml.safe_dump(stored, sort_keys=False))
    capsys.readouterr()

    assert run_cli(["list", "--all"]) == 0

    captured = capsys.readouterr()
    assert "Deleted 1 range destroyed more than 30 days ago" in captured.err
    assert not (home_root / "ranges" / str(old)).exists()
    assert str(old) not in captured.out and str(recent) in captured.out


def test_update_reports_a_modified_parameter(
    lab_dir: Path, tmp_path: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    range_id = build_range(lab_dir, capsys, "--provider", "aws")
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    text = (lab_dir / "lab.server-binding.aws.yaml").read_text().replace("t3.micro", "t3.large")
    (overlay / "lab.server-binding.aws.yaml").write_text(text)
    terraform_calls.clear()

    assert run_cli(["update", "add", str(range_id), str(overlay)]) == 0

    out = capsys.readouterr().out
    assert "modified" in out and "ServerBinding app-1-aws" in out
    assert "spec.aws.instanceType" in out and "updated" in out
    assert [call[0] for call in terraform_calls] == ["init", "apply", "output"]


def test_update_add_applies_region_and_perimeter_overrides(
    home_root: Path, lab_dir: Path, tmp_path: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    range_id = build_range(lab_dir, capsys, "--provider", "aws")
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    text = (lab_dir / "lab.server-binding.aws.yaml").read_text().replace("eu-central-1", "eu-west-2")
    (overlay / "lab.server-binding.aws.yaml").write_text(text)
    terraform_calls.clear()

    code = run_cli([
        "update", "add", str(range_id), str(overlay),
        "--set", "*.spec.location=eu-west-1",
        "--set", "lab.spec.perimeter.sources=[198.51.100.4/32, 203.0.113.8/32]",
    ])

    assert code == 0
    documents = home_root / "ranges" / str(range_id) / "documents"
    aws_binding = (documents / "app-1-aws.server-binding.yaml").read_text()
    network_binding = (documents / "lab-aws.network-binding.yaml").read_text()
    azure_binding = (documents / "lab-azure.network-binding.yaml").read_text()
    network = (documents / "lab.network.yaml").read_text()
    assert "eu-west-1" in aws_binding and "eu-west-2" not in aws_binding
    assert "eu-west-1" in network_binding
    assert "westeurope" in azure_binding
    assert "198.51.100.4/32" in network and "203.0.113.8/32" in network
    assert "203.0.113.10/32" not in network
    assert record(home_root, range_id)["location"] == "eu-west-1"
    assert [call[0] for call in terraform_calls] == ["init", "apply", "output"]


def test_update_add_rejects_a_perimeter_inside_the_address_space(
    home_root: Path, lab_dir: Path, tmp_path: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    range_id = build_range(lab_dir, capsys, "--provider", "aws")
    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "lab.server-binding.aws.yaml").write_text((lab_dir / "lab.server-binding.aws.yaml").read_text())
    terraform_calls.clear()

    code = run_cli([
        "update", "add", str(range_id), str(overlay),
        "--set", "lab.spec.perimeter.sources=[10.0.1.10/32]",
    ])

    assert code == 1
    assert "inside the address space" in capsys.readouterr().err
    assert terraform_calls == []
    network = (home_root / "ranges" / str(range_id) / "documents" / "lab.network.yaml").read_text()
    assert "203.0.113.10/32" in network
    assert record(home_root, range_id)["location"] == "eu-central-1"


def test_update_remove_rejects_a_binding_without_its_server(
    lab_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    range_id = build_range(lab_dir, capsys, "--provider", "aws")
    terraform_calls.clear()

    assert run_cli(["update", "remove", str(range_id), "lab.server-binding.aws.yaml"]) == 1

    assert "cannot be removed without server 'app-1'" in capsys.readouterr().err
    assert terraform_calls == []


def test_get_prints_one_range(lab_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]) -> None:
    range_id = build_range(lab_dir, capsys, "--provider", "aws")

    assert run_cli(["get", str(range_id)]) == 0

    out = capsys.readouterr().out
    assert "lab on aws" in out and "built" in out
    assert str(range_id) in out and "tester" in out and "eu-central-1" in out
    assert "10.0.0.0/16" in out and "subnet-2" in out
    assert "app-1" in out and "ubuntu" in out and "t3.micro" in out and "10.0.1.10" in out
    assert "history" in out and "created" in out


def test_get_unknown_range(capsys: pytest.CaptureFixture[str]) -> None:
    missing = uuid4()

    assert run_cli(["get", str(missing)]) == 1

    assert str(missing) in capsys.readouterr().err


def test_build_prints_servers(ar_template_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["build", str(ar_template_dir), "--local-state"]) == 0

    assert [call[0] for call in terraform_calls] == ["init", "apply", "output"]
    out = capsys.readouterr().out
    assert "ar on aws  built" in out
    assert "win" in out and "10.0.2.11" in out


def test_build_from_single_file(
    tmp_path: Path, home_root: Path, ar_template_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]
) -> None:
    combined = tmp_path / "ar.yaml"
    combined.write_text("\n---\n".join(path.read_text() for path in sorted(ar_template_dir.glob("*.yaml"))))

    range_id = build_range(combined, capsys)

    assert [path.name for path in (home_root / "ranges" / str(range_id) / "documents").iterdir()] == ["ar.yaml"]


def test_destroy_needs_yes_without_terminal(terraform_calls, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    assert run_cli(["destroy", str(uuid4())]) == 2
    assert terraform_calls == []


def test_destroy_cancelled(
    home_root: Path, ar_template_dir: Path, terraform_calls, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    range_id = build_range(ar_template_dir, capsys)
    terraform_calls.clear()
    prompts: list[str] = []
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "no")

    assert run_cli(["destroy", str(range_id)]) == 1
    assert terraform_calls == []
    assert f"ar on aws ({range_id})" in prompts[0]
    assert record(home_root, range_id)["state"] == "built"


def test_destroy_unknown_range(terraform_calls, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["destroy", str(uuid4()), "--yes"]) == 1
    assert terraform_calls == []
    assert "no cyber range with id" in capsys.readouterr().err


def test_destroy_needs_a_uuid(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(["destroy", "ar", "--yes"]) == 2
    assert "invalid UUID value" in capsys.readouterr().err


def test_first_run_asks_for_a_user_name_and_password(
    home_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (home_root / "config.yaml").unlink()
    answers = iter(["", "nope!", "Ada"])
    passwords = iter(["short", "GoodPass1!", "GoodPass1!"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(passwords))

    assert run_cli(["list"]) == 0

    assert yaml.safe_load((home_root / "config.yaml").read_text()) == {
        "user_name": "ada",
        "password": "GoodPass1!",
    }
    captured = capsys.readouterr()
    assert "Enter a user name" in captured.err
    assert "Enter a password" in captured.err
    assert "No cyber ranges" in captured.out


def test_first_run_without_a_terminal_stops(
    home_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (home_root / "config.yaml").unlink()
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    assert run_cli(["list"]) == 2

    assert "user_name" in capsys.readouterr().err
    assert not (home_root / "config.yaml").exists()


def test_init_replaces_the_stored_user_name_and_password(
    home_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["Ada"])
    passwords = iter(["NewPass1!", "NewPass1!"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(passwords))

    assert run_cli(["init"]) == 0

    config = home_root / "config.yaml"
    assert yaml.safe_load(config.read_text()) == {"user_name": "ada", "password": "NewPass1!"}
    captured = capsys.readouterr()
    assert "This replaces" in captured.err
    assert f"Stored user name ada in {config}" in captured.out


def test_init_refuses_while_a_range_is_built(
    home_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    built = RangeRecord.new(name="ar", provider="aws", location="eu-west-1", source="tmp/ar").transition(
        RangeState.BUILDING
    ).transition(RangeState.BUILT)
    destroyed = (
        RangeRecord.new(name="old", provider="aws", location="eu-west-1", source="tmp/ar")
        .transition(RangeState.BUILDING)
        .transition(RangeState.BUILT)
        .transition(RangeState.DESTROYING)
        .transition(RangeState.DESTROYED)
    )
    store = YamlRangeStore(AttackRangeHome(home_root))
    store.create(built)
    store.create(destroyed)
    original = (home_root / "config.yaml").read_text()

    def unexpected_prompt(prompt: str) -> str:
        raise AssertionError(prompt)

    monkeypatch.setattr("builtins.input", unexpected_prompt)

    assert run_cli(["init"]) == 1

    assert (home_root / "config.yaml").read_text() == original
    err = capsys.readouterr().err
    assert str(built.id) in err and "is built" in err
    assert str(destroyed.id) not in err


def test_init_without_a_terminal_keeps_the_stored_config(
    home_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original = (home_root / "config.yaml").read_text()
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    assert run_cli(["init"]) == 2

    assert (home_root / "config.yaml").read_text() == original
    assert "needs a terminal" in capsys.readouterr().err


def test_invalid_template_fails(lab_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]) -> None:
    code = run_cli(["plan", str(lab_dir)])

    assert code == 1
    assert terraform_calls == []
    assert "choose a provider" in capsys.readouterr().err

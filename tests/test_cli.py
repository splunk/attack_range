import json
import re
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

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


def test_invalid_template_fails(lab_dir: Path, terraform_calls, capsys: pytest.CaptureFixture[str]) -> None:
    code = run_cli(["plan", str(lab_dir)])

    assert code == 1
    assert terraform_calls == []
    assert "choose a provider" in capsys.readouterr().err

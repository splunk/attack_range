from pathlib import Path

import pytest
import yaml

from attack_range_infrastructure.storage import (
    AttackRangeHome,
    UserConfig,
    UserConfigError,
    ensure_user_config,
    reset_user_config,
)
from attack_range_infrastructure.storage.user_config import password_problem
from attack_range_infrastructure.terraform.renderers.base import RenderError, cloud_name
from conftest import RESOURCE_PREFIX, identified, load_cyber_range


def test_missing_config_has_no_user_name(home: AttackRangeHome) -> None:
    home.config_file.unlink()

    assert UserConfig.load(home) is None


def test_user_name_is_read_in_lowercase(home: AttackRangeHome) -> None:
    home.config_file.write_text("user_name: Ada\npassword: Test123!\n")

    assert UserConfig.load(home) == UserConfig("ada", "Test123!")


def test_unusable_user_name_is_missing(home: AttackRangeHome) -> None:
    home.config_file.write_text("user_name: bad name\npassword: Test123!\n")

    assert UserConfig.load(home) is None


def test_password_must_mix_letters_numbers_and_a_special_character() -> None:
    assert password_problem("short1!") is not None
    assert password_problem("longpassword!") is not None
    assert password_problem("longpassword1") is not None
    assert password_problem("12345678!") is not None
    assert password_problem("GoodPass1!") is None


def test_first_run_asks_until_the_name_and_password_are_usable(
    home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.config_file.unlink()
    answers = iter(["", "Bad Name", "Ada"])
    passwords = iter(["short", "GoodPass1!", "WrongPass1!", "GoodPass1!", "GoodPass1!"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(passwords))

    config = ensure_user_config(home)

    assert config == UserConfig("ada", "GoodPass1!")
    assert yaml.safe_load(home.config_file.read_text()) == {"user_name": "ada", "password": "GoodPass1!"}
    assert home.config_file.stat().st_mode & 0o777 == 0o600
    assert ensure_user_config(home) == config


def test_existing_user_name_asks_only_for_a_password(
    home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.config_file.write_text("user_name: Ada\n")
    passwords = iter(["GoodPass1!", "GoodPass1!"])

    def unexpected_name_prompt(prompt: str) -> str:
        raise AssertionError(prompt)

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", unexpected_name_prompt)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(passwords))

    assert ensure_user_config(home) == UserConfig("ada", "GoodPass1!")


def test_first_run_without_a_terminal_explains_the_file(home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch) -> None:
    home.config_file.unlink()
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    with pytest.raises(UserConfigError, match="No user name"):
        ensure_user_config(home)

    assert not home.config_file.exists()


def test_missing_password_without_a_terminal_explains_the_rule(
    home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.config_file.write_text("user_name: ada\n")
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    with pytest.raises(UserConfigError, match="no usable password"):
        ensure_user_config(home)


def test_reset_replaces_the_stored_user_name_and_password(
    home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = iter(["", "Ada"])
    passwords = iter(["NewPass1!", "nope", "NewPass1!", "NewPass1!"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(passwords))

    config = reset_user_config(home)

    assert config == UserConfig("ada", "NewPass1!")
    assert yaml.safe_load(home.config_file.read_text()) == {"user_name": "ada", "password": "NewPass1!"}
    assert home.config_file.stat().st_mode & 0o777 == 0o600


def test_reset_without_a_terminal_keeps_the_stored_config(
    home: AttackRangeHome, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = home.config_file.read_text()
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    with pytest.raises(UserConfigError, match="needs a terminal"):
        reset_user_config(home)

    assert home.config_file.read_text() == original


def test_cloud_name_uses_the_range_id_and_user(lab_dir: Path) -> None:
    cyber_range = identified(load_cyber_range(lab_dir, "aws"))

    assert cloud_name(cyber_range, "win") == f"win-{RESOURCE_PREFIX}-tester"
    assert cloud_name(cyber_range, "app-1", limit=15) == f"app-1-{RESOURCE_PREFIX}"
    short_user = identified(load_cyber_range(lab_dir, "aws"), user_name="a")
    assert cloud_name(short_user, "win", limit=15) == f"win-{RESOURCE_PREFIX}-a"


def test_cloud_name_needs_an_id_and_a_user(lab_dir: Path) -> None:
    with pytest.raises(RenderError, match="user name"):
        cloud_name(load_cyber_range(lab_dir, "aws"), "win")

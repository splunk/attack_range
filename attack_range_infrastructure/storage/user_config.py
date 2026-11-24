"""The user name and password stored in `config.yaml` of the attack range home folder."""

import getpass
import re
import sys
from dataclasses import dataclass

import yaml

from .home import AttackRangeHome

_USER_NAME = re.compile(r"^[a-z](?:[a-z0-9-]{0,30}[a-z0-9])?$")
_NAME_RULE = (
    "Use 1 to 32 characters: start with a lowercase letter, then lowercase letters, "
    "digits, or hyphens, and do not end with a hyphen."
)
_PASSWORD_RULE = "Use at least 8 characters, including a letter, a number, and a special character."


class UserConfigError(ValueError):
    """Raised when the user config cannot be read or is not set in a context that cannot ask."""


@dataclass(frozen=True)
class UserConfig:
    """The operator of this attack range install."""

    user_name: str
    password: str

    @classmethod
    def load(cls, home: AttackRangeHome) -> "UserConfig | None":
        """Return the stored user name and password, or None when either is missing.

        A name is stored in lowercase. `Ada` and ` ada ` are read as `ada`.
        The password is stored as entered.
        """
        user_name, password = _usable(home)
        if user_name is None or password is None:
            return None
        return cls(user_name, password)

    def save(self, home: AttackRangeHome) -> None:
        home.root.mkdir(parents=True, exist_ok=True)
        home.config_file.write_text(
            yaml.safe_dump(
                {"user_name": self.user_name, "password": self.password},
                sort_keys=False,
            )
        )
        home.config_file.chmod(0o600)


def user_name_problem(user_name: str) -> str | None:
    """Return why `user_name` cannot be used, or None when it can."""
    if _USER_NAME.fullmatch(user_name):
        return None
    return _NAME_RULE


def password_problem(password: str) -> str | None:
    """Return why `password` cannot be used, or None when it can.

    A usable password is at least 8 characters and contains a letter, a number,
    and a character that is neither.
    """
    has_letter = any(character.isalpha() for character in password)
    has_number = any(character.isdigit() for character in password)
    has_special = any(not character.isalnum() for character in password)
    if len(password) >= 8 and has_letter and has_number and has_special:
        return None
    return _PASSWORD_RULE


def ensure_user_config(home: AttackRangeHome) -> UserConfig:
    """Return the stored user name and password, asking for whatever is missing.

    The first run asks for both and stores them in the home folder. A later run
    asks only for a value that is still missing.
    """
    user_name, password = _usable(home)
    if user_name is not None and password is not None:
        return UserConfig(user_name, password)
    if not sys.stdin.isatty():
        raise _unattended(home, user_name, password)
    if user_name is None:
        user_name = _ask_user_name(home)
    if password is None:
        password = _ask_password(home)
    config = UserConfig(user_name, password)
    config.save(home)
    return config


def reset_user_config(home: AttackRangeHome) -> UserConfig:
    """Ask for a user name and password and replace the stored values.

    Ranges that are already built keep the user name they were built with.
    """
    if not sys.stdin.isatty():
        raise UserConfigError(f"Setting the user name and password in {home.config_file} needs a terminal.")
    if home.config_file.is_file():
        print(
            f"This replaces the user name and password in {home.config_file}. "
            "Ranges already built keep the user name they were built with.",
            file=sys.stderr,
        )
    config = UserConfig(_ask_user_name(home), _ask_password(home))
    config.save(home)
    return config


def _usable(home: AttackRangeHome) -> tuple[str | None, str | None]:
    path = home.config_file
    if not path.is_file():
        return None, None
    try:
        loaded = yaml.safe_load(path.read_text())
    except yaml.YAMLError as error:
        raise UserConfigError(f"{path} is not valid YAML: {error}") from error
    if loaded is None:
        return None, None
    if not isinstance(loaded, dict):
        raise UserConfigError(f"{path} must be a mapping")
    return _user_name_value(loaded.get("user_name")), _password_value(loaded.get("password"))


def _user_name_value(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    user_name = raw.strip().lower()
    if user_name_problem(user_name) is not None:
        return None
    return user_name


def _password_value(raw: object) -> str | None:
    if not isinstance(raw, str) or password_problem(raw) is not None:
        return None
    return raw


def _unattended(home: AttackRangeHome, user_name: str | None, password: str | None) -> UserConfigError:
    path = home.config_file
    if not path.is_file():
        return UserConfigError(
            f"No user name in {path}. Run attack-range in a terminal to set one, "
            "or write user_name and password there."
        )
    if user_name is None:
        return UserConfigError(f"{path} has no usable user_name. {_NAME_RULE}")
    return UserConfigError(f"{path} has no usable password. {_PASSWORD_RULE}")


def _ask_user_name(home: AttackRangeHome) -> str:
    print(
        "Enter a user name. Attack range stores it in "
        f"{home.config_file} and names cloud resources <resource>-<range id>-<user name>.",
        file=sys.stderr,
    )
    while True:
        try:
            entered = input("User name: ")
        except EOFError as error:
            raise UserConfigError("No user name entered.") from error
        user_name = entered.strip().lower()
        problem = user_name_problem(user_name)
        if problem is None:
            return user_name
        print(problem, file=sys.stderr)


def _ask_password(home: AttackRangeHome) -> str:
    print(
        f"Enter a password. Attack range stores it in {home.config_file}. {_PASSWORD_RULE}",
        file=sys.stderr,
    )
    while True:
        try:
            password = getpass.getpass("Password: ")
        except EOFError as error:
            raise UserConfigError("No password entered.") from error
        problem = password_problem(password)
        if problem is not None:
            print(problem, file=sys.stderr)
            continue
        try:
            confirm = getpass.getpass("Confirm password: ")
        except EOFError as error:
            raise UserConfigError("No password entered.") from error
        if password == confirm:
            return password
        print("The passwords do not match.", file=sys.stderr)

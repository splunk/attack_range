import dataclasses
import shutil
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from attack_range.application.cyber_range import CyberRange
from attack_range.domain.entities.common import Provider
from attack_range_infrastructure.storage import AttackRangeHome, FileCyberRangeRepository

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "tmp"
PLACEHOLDER_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKeyForLabSpecOnly"
VALID_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIEE0Oo0Q8Y7TZMkct9Xi2MkHv4q2eVL1/tCGudvIJQn"


RESOURCE_PREFIX = "e6fffcb8"
RESOURCE_ID = UUID(f"{RESOURCE_PREFIX}-0000-4000-8000-000000000001")
RESOURCE_USER = "tester"


@pytest.fixture(autouse=True)
def home_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep every test away from the real ~/.attack_range."""
    root = tmp_path / "home"
    root.mkdir()
    (root / "config.yaml").write_text(f"user_name: {RESOURCE_USER}\npassword: Test123!\n")
    monkeypatch.setenv("ATTACK_RANGE_HOME", str(root))
    return root


@pytest.fixture
def home(home_root: Path) -> AttackRangeHome:
    return AttackRangeHome(home_root).ensure()


@pytest.fixture
def ar_template_dir() -> Path:
    return EXAMPLES / "ar_template"


@pytest.fixture
def lab_dir(tmp_path: Path) -> Path:
    """Copy of the tmp/ lab documents with its user data file and a public key Azure accepts."""
    lab = tmp_path / "lab"
    lab.mkdir()
    for document in EXAMPLES.glob("*.yaml"):
        shutil.copy(document, lab / document.name)
    server = lab / "lab.server.yaml"
    server.write_text(server.read_text().replace(PLACEHOLDER_KEY, VALID_KEY))
    (lab / "user-data").mkdir()
    (lab / "user-data" / "app-1.ps1").write_text("Write-Host ${env:COMPUTERNAME}\n")
    return lab


def load_cyber_range(path: Path, provider: Provider | None = None) -> CyberRange:
    return FileCyberRangeRepository().load(path, provider)


def identified(cyber_range: CyberRange, user_name: str = RESOURCE_USER) -> CyberRange:
    """Give a template the id and user name that cloud resource names are built from."""
    return dataclasses.replace(
        cyber_range,
        id=cyber_range.id or RESOURCE_ID,
        user_name=cyber_range.user_name or user_name,
    )


def registered(cyber_range: CyberRange, local_state: bool = False) -> CyberRange:
    """The range as Build hands it to the provisioner, with a fresh id."""
    return dataclasses.replace(cyber_range, id=uuid4(), local_state=local_state)


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, f"{old!r} not in {path.name}"
    path.write_text(text.replace(old, new))

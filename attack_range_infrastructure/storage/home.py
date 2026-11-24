"""Layout of the attack range home folder, `~/.attack_range` unless ATTACK_RANGE_HOME is set."""

import os
from pathlib import Path
from typing import Optional
from uuid import UUID

HOME_VARIABLE = "ATTACK_RANGE_HOME"


class AttackRangeHome:
    """Paths of the home folder.

    config.yaml                  user name and password, asked for on first use
    ranges/<id>/range.yaml       state record
    ranges/<id>/documents/       copy of the template
    ranges/<id>/keys/            SSH key pair used by AWS servers and the WireGuard gateway
    ranges/<id>/wireguard/       WireGuard client config of an AWS or Azure range
    ranges/<id>/terraform/       generated code and local state
    plans/<name>-<provider>/     scratch folder of `plan`
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root or os.environ.get(HOME_VARIABLE) or Path.home() / ".attack_range").expanduser()

    def ensure(self) -> "AttackRangeHome":
        """Create the folders on first use."""
        self.ranges_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def config_file(self) -> Path:
        return self.root / "config.yaml"

    @property
    def ranges_dir(self) -> Path:
        return self.root / "ranges"

    @property
    def plans_dir(self) -> Path:
        return self.root / "plans"

    def range_dir(self, range_id: UUID) -> Path:
        return self.ranges_dir / str(range_id)

    def record_file(self, range_id: UUID) -> Path:
        return self.range_dir(range_id) / "range.yaml"

    def documents_dir(self, range_id: UUID) -> Path:
        return self.range_dir(range_id) / "documents"

    def keys_dir(self, range_id: UUID) -> Path:
        return self.range_dir(range_id) / "keys"

    def wireguard_config(self, range_id: UUID) -> Path:
        return self.range_dir(range_id) / "wireguard" / "client.conf"

    def terraform_dir(self, range_id: UUID) -> Path:
        return self.range_dir(range_id) / "terraform"

    def plan_dir(self, name: str, provider: str) -> Path:
        return self.plans_dir / f"{name}-{provider}"

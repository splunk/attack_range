from pathlib import Path

import pytest

from attack_range_infrastructure.keys import PUBLIC_KEY, KeyPairError, RangeKeyPair


def test_ensure_creates_a_pair_and_then_reuses_it(tmp_path: Path) -> None:
    pair = RangeKeyPair(tmp_path / "keys")

    first = pair.ensure()
    second = pair.ensure()

    assert first.startswith("ssh-rsa ")
    assert second == first
    assert pair.private_key.read_text().startswith("-----BEGIN OPENSSH PRIVATE KEY-----")
    assert pair.private_key.stat().st_mode & 0o777 == 0o600
    assert pair.directory.stat().st_mode & 0o777 == 0o700


def test_half_a_pair_is_rejected(tmp_path: Path) -> None:
    directory = tmp_path / "keys"
    directory.mkdir()
    (directory / PUBLIC_KEY).write_text("ssh-rsa AAAA\n")

    with pytest.raises(KeyPairError, match="missing"):
        RangeKeyPair(directory).ensure()

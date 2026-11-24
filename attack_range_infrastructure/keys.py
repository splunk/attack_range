"""SSH key pair stored with one cyber range."""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

PRIVATE_KEY = "id_rsa"
PUBLIC_KEY = "id_rsa.pub"
# 2048-bit RSA is the key type EC2 accepts for both Linux and Windows AMIs.
KEY_SIZE = 2048


class KeyPairError(ValueError):
    """Raised when a range key pair is incomplete and cannot be reused."""


class RangeKeyPair:
    """An RSA key pair in a directory. The private key stays on disk."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.private_key = directory / PRIVATE_KEY
        self.public_key = directory / PUBLIC_KEY

    def ensure(self) -> str:
        """Return the OpenSSH public key, generating the pair the first time."""
        private_exists = self.private_key.is_file()
        public_exists = self.public_key.is_file()
        if private_exists and public_exists:
            return self.public_key.read_text().strip()
        if private_exists or public_exists:
            raise KeyPairError(f"key pair in {self.directory} is missing its private or public key")
        return self._generate()

    def _generate(self) -> str:
        private = rsa.generate_private_key(public_exponent=65537, key_size=KEY_SIZE)
        private_bytes = private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = private.public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        self.private_key.write_bytes(private_bytes)
        self.private_key.chmod(0o600)
        self.public_key.write_bytes(public_bytes + b"\n")
        self.public_key.chmod(0o644)
        return public_bytes.decode().strip()

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet, InvalidToken


@dataclass
class SeedVault:
    """Encrypts and persists seed phrases/private keys on disk."""

    path: Path
    iterations: int = 390_000

    @classmethod
    def default(cls, path: Optional[str]) -> "SeedVault":
        target = Path(os.path.expanduser(path or "~/.solcodex/seed_vault.json"))
        target.parent.mkdir(parents=True, exist_ok=True)
        return cls(path=target)

    def exists(self) -> bool:
        return self.path.exists()

    def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))

    def save(self, secret: str, passphrase: str) -> None:
        salt = os.urandom(16)
        key = self._derive_key(passphrase, salt)
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(secret.encode()).decode()
        payload = {
            "salt": base64.b64encode(salt).decode(),
            "ciphertext": ciphertext,
        }
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self, passphrase: str) -> str:
        if not self.path.exists():
            raise FileNotFoundError("Vault file not found")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        salt = base64.b64decode(payload["salt"])
        key = self._derive_key(passphrase, salt)
        fernet = Fernet(key)
        try:
            return fernet.decrypt(payload["ciphertext"].encode()).decode()
        except InvalidToken as exc:  # pragma: no cover - runtime safety
            raise PermissionError("Invalid vault passphrase") from exc


__all__ = ["SeedVault"]

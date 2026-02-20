from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from argon2.low_level import Type, hash_secret_raw

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class KDFParams:
    time_cost: int = 3
    memory_cost: int = 65536
    parallelism: int = 2
    hash_len: int = 32


class KeystoreError(RuntimeError):
    pass


class Keystore:
    def __init__(self, settings: Settings | None = None, passphrase: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.path = self.settings.config_dir / "keystore.json"
        self.passphrase = passphrase or os.getenv("CB_ORGANIZER_PASSPHRASE")
        self.kdf = KDFParams()

    def load(self) -> dict[str, object] | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, object]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def derive_wrapping_key(self, passphrase: str, salt: bytes) -> bytes:
        return hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=salt,
            time_cost=self.kdf.time_cost,
            memory_cost=self.kdf.memory_cost,
            parallelism=self.kdf.parallelism,
            hash_len=self.kdf.hash_len,
            type=Type.ID,
        )

    def create_if_missing(self, random_kek: bytes, wrapped_kek: bytes, salt: bytes) -> dict[str, object]:
        existing = self.load()
        if existing:
            return existing
        payload: dict[str, object] = {
            "version": 1,
            "kdf": {
                "type": "argon2id",
                "time_cost": self.kdf.time_cost,
                "memory_cost": self.kdf.memory_cost,
                "parallelism": self.kdf.parallelism,
                "hash_len": self.kdf.hash_len,
            },
            "salt_b64": base64.b64encode(salt).decode("utf-8"),
            "wrapped_kek_b64": base64.b64encode(wrapped_kek).decode("utf-8"),
            "kek_sha256": hashlib.sha256(random_kek).hexdigest(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.save(payload)
        return payload

    def derive_wrapping_key_from_store(self, payload: dict[str, object]) -> tuple[bytes, bytes]:
        if not self.passphrase:
            raise KeystoreError("Vault passphrase is required to unlock encrypted data.")
        salt_b64 = payload.get("salt_b64")
        if not isinstance(salt_b64, str):
            raise KeystoreError("Invalid keystore payload: missing salt.")
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        wrapping_key = self.derive_wrapping_key(self.passphrase, salt)
        return wrapping_key, salt

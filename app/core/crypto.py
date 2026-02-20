from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from typing import Optional

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap, aes_key_wrap

from app.core.config import Settings
from app.core.keystore import Keystore, KeystoreError
from app.core.logging import get_logger

KEYRING_SERVICE = "cb_organizer"
KEYRING_USER = "local_kek_v1"
FIELD_HEADER_V1 = b"CBF1"
FIELD_AAD_V1 = b"cb-organizer-field-v1"
logger = get_logger(__name__)


@dataclass(slots=True)
class CipherBlob:
    nonce: bytes
    ciphertext: bytes


class KeyManager:
    def __init__(self, passphrase: Optional[str] = None, settings: Settings | None = None) -> None:
        self.keystore = Keystore(settings=settings, passphrase=passphrase)
        self.disable_keyring = os.getenv("CB_DISABLE_KEYRING", "0") == "1"

    def _get_keyring_value(self) -> bytes | None:
        if self.disable_keyring:
            return None
        try:
            stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        except Exception:
            return None
        if not stored:
            return None
        return base64.b64decode(stored.encode("utf-8"))

    def _set_keyring_value(self, kek: bytes) -> None:
        if self.disable_keyring:
            return
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USER, base64.b64encode(kek).decode("utf-8"))
        except Exception as exc:
            logger.warning("Keyring storage unavailable; continuing with passphrase unlock (%s)", type(exc).__name__)

    def get_or_create_kek(self) -> bytes:
        payload = self.keystore.load()

        if payload is None:
            if not self.keystore.passphrase:
                raise KeystoreError("Vault passphrase is required for first-time encryption setup.")
            salt = os.urandom(16)
            wrapping_key = self.keystore.derive_wrapping_key(self.keystore.passphrase, salt)
            kek = os.urandom(32)
            wrapped_kek = wrap_key(kek, wrapping_key)
            payload = self.keystore.create_if_missing(kek, wrapped_kek, salt)
            self._set_keyring_value(kek)
            return kek

        keyring_kek = self._get_keyring_value()
        expected_hash = payload.get("kek_sha256")
        if keyring_kek is not None and isinstance(expected_hash, str):
            if hashlib.sha256(keyring_kek).hexdigest() == expected_hash:
                return keyring_kek

        wrapped_b64 = payload.get("wrapped_kek_b64")
        if not isinstance(wrapped_b64, str):
            raise KeystoreError("Invalid keystore payload: missing wrapped KEK.")
        wrapping_key, _ = self.keystore.derive_wrapping_key_from_store(payload)
        wrapped = base64.b64decode(wrapped_b64.encode("utf-8"))
        kek = unwrap_key(wrapped, wrapping_key)
        if isinstance(expected_hash, str) and hashlib.sha256(kek).hexdigest() != expected_hash:
            raise KeystoreError("Keystore integrity check failed.")
        self._set_keyring_value(kek)
        return kek


def encrypt_bytes(plaintext: bytes, key: bytes, aad: bytes | None = None) -> CipherBlob:
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return CipherBlob(nonce=nonce, ciphertext=ciphertext)


def decrypt_bytes(blob: CipherBlob, key: bytes, aad: bytes | None = None) -> bytes:
    return AESGCM(key).decrypt(blob.nonce, blob.ciphertext, aad)


def wrap_key(dek: bytes, kek: bytes) -> bytes:
    return aes_key_wrap(kek, dek)


def unwrap_key(wrapped_dek: bytes, kek: bytes) -> bytes:
    return aes_key_unwrap(kek, wrapped_dek)


class FieldEncryptor:
    def __init__(self, key_manager: Optional[KeyManager] = None) -> None:
        self.key_manager = key_manager or KeyManager()

    def encrypt(self, value: str) -> str:
        key = self.key_manager.get_or_create_kek()
        blob = encrypt_bytes(value.encode("utf-8"), key, aad=FIELD_AAD_V1)
        payload = FIELD_HEADER_V1 + blob.nonce + blob.ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt(self, value: str) -> str:
        raw = base64.b64decode(value.encode("utf-8"))
        key = self.key_manager.get_or_create_kek()
        if raw.startswith(FIELD_HEADER_V1):
            payload = raw[len(FIELD_HEADER_V1) :]
            blob = CipherBlob(nonce=payload[:12], ciphertext=payload[12:])
            return decrypt_bytes(blob, key, aad=FIELD_AAD_V1).decode("utf-8")

        # Backward compatibility for pre-versioned ciphertexts.
        blob = CipherBlob(nonce=raw[:12], ciphertext=raw[12:])
        return decrypt_bytes(blob, key, aad=None).decode("utf-8")

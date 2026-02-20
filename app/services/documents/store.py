from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.crypto import KeyManager, wrap_key, unwrap_key


def _canonical_aad(storage_path: str, sha256_plaintext: str, size_bytes: int, encryption_version: int) -> bytes:
    payload = {
        "v": encryption_version,
        "storage_path": storage_path,
        "sha256_plaintext": sha256_plaintext,
        "size_bytes": size_bytes,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class DocumentStore:
    def __init__(self, docs_root: Path) -> None:
        self.docs_root = docs_root
        self.docs_root.mkdir(parents=True, exist_ok=True)
        self.key_manager = KeyManager()

    def _atomic_write(self, path: Path, content: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        try:
            dir_fd = os.open(str(path.parent), os.O_DIRECTORY)
        except Exception:
            return
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    def encrypt_and_store(self, filename: str, payload: bytes) -> dict[str, bytes | str | int]:
        plaintext_hash = hashlib.sha256(payload).hexdigest()
        dek = os.urandom(32)
        nonce = os.urandom(12)
        relative = f"{uuid4().hex}.bin"
        encryption_version = 1
        aad = _canonical_aad(relative, plaintext_hash, len(payload), encryption_version)
        ciphertext = AESGCM(dek).encrypt(nonce, payload, aad)
        path = self.docs_root / relative
        self._atomic_write(path, ciphertext)
        cipher_hash = hashlib.sha256(ciphertext).hexdigest()
        wrapped = wrap_key(dek, self.key_manager.get_or_create_kek())
        aad_hash = hashlib.sha256(aad).hexdigest()
        return {
            "filename": filename,
            "storage_path": relative,
            "nonce": nonce,
            "wrapped_dek": wrapped,
            "sha256_plaintext": plaintext_hash,
            "sha256_ciphertext": cipher_hash,
            "aad_sha256": aad_hash,
            "encryption_version": encryption_version,
            "size_bytes": len(payload),
        }

    def decrypt_and_verify(
        self,
        storage_path: str,
        nonce: bytes,
        wrapped_dek: bytes,
        expected_sha256_ciphertext: str,
        expected_sha256_plaintext: str,
        size_bytes: int,
        encryption_version: int = 1,
    ) -> bytes:
        ciphertext = (self.docs_root / storage_path).read_bytes()
        if hashlib.sha256(ciphertext).hexdigest() != expected_sha256_ciphertext:
            raise ValueError("Ciphertext integrity check failed")
        dek = unwrap_key(wrapped_dek, self.key_manager.get_or_create_kek())
        aad = _canonical_aad(storage_path, expected_sha256_plaintext, size_bytes, encryption_version)
        plaintext = AESGCM(dek).decrypt(nonce, ciphertext, aad)
        if hashlib.sha256(plaintext).hexdigest() != expected_sha256_plaintext:
            raise ValueError("Plaintext integrity check failed")
        return plaintext

    def decrypt(self, storage_path: str, nonce: bytes, wrapped_dek: bytes) -> bytes:
        ciphertext = (self.docs_root / storage_path).read_bytes()
        dek = unwrap_key(wrapped_dek, self.key_manager.get_or_create_kek())
        return AESGCM(dek).decrypt(nonce, ciphertext, None)

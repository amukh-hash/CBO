from pathlib import Path

from app.services.documents.store import DocumentStore


def test_document_encryption_roundtrip_and_hash(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
    payload = b"receipt-pdf-binary"
    meta = store.encrypt_and_store("receipt.pdf", payload)
    decrypted = store.decrypt_and_verify(
        storage_path=str(meta["storage_path"]),
        nonce=meta["nonce"],
        wrapped_dek=meta["wrapped_dek"],
        expected_sha256_ciphertext=str(meta["sha256_ciphertext"]),
        expected_sha256_plaintext=str(meta["sha256_plaintext"]),
        size_bytes=int(meta["size_bytes"]),
        encryption_version=int(meta["encryption_version"]),
    )
    assert decrypted == payload
    stored = (tmp_path / str(meta["storage_path"])).read_bytes()
    import hashlib

    assert hashlib.sha256(stored).hexdigest() == meta["sha256_ciphertext"]


def test_document_decrypt_fails_on_tamper(tmp_path: Path) -> None:
    store = DocumentStore(tmp_path)
    meta = store.encrypt_and_store("receipt.pdf", b"abc123")
    path = tmp_path / str(meta["storage_path"])
    bytes_mut = bytearray(path.read_bytes())
    bytes_mut[0] ^= 0x01
    path.write_bytes(bytes(bytes_mut))
    import pytest

    with pytest.raises(ValueError):
        store.decrypt_and_verify(
            storage_path=str(meta["storage_path"]),
            nonce=meta["nonce"],
            wrapped_dek=meta["wrapped_dek"],
            expected_sha256_ciphertext=str(meta["sha256_ciphertext"]),
            expected_sha256_plaintext=str(meta["sha256_plaintext"]),
            size_bytes=int(meta["size_bytes"]),
            encryption_version=int(meta["encryption_version"]),
        )

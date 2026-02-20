from __future__ import annotations

import base64

import pytest

from app.core.config import Settings
from app.core.crypto import FIELD_HEADER_V1, FieldEncryptor, KeyManager


def _settings_for(tmp_path):
    settings = Settings(data_dir=tmp_path)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    return settings


def test_keystore_persists_kek_without_keyring(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CB_DISABLE_KEYRING", "1")
    settings = _settings_for(tmp_path)

    km1 = KeyManager(passphrase="passphrase-a", settings=settings)
    kek1 = km1.get_or_create_kek()

    km2 = KeyManager(passphrase="passphrase-a", settings=settings)
    kek2 = km2.get_or_create_kek()

    assert kek1 == kek2


def test_wrong_passphrase_fails_unlock(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CB_DISABLE_KEYRING", "1")
    settings = _settings_for(tmp_path)

    km_ok = KeyManager(passphrase="right-pass", settings=settings)
    km_ok.get_or_create_kek()

    km_bad = KeyManager(passphrase="wrong-pass", settings=settings)
    with pytest.raises(Exception):
        km_bad.get_or_create_kek()


def test_field_ciphertext_has_version_header() -> None:
    enc = FieldEncryptor()
    raw = base64.b64decode(enc.encrypt("abc").encode("utf-8"))
    assert raw.startswith(FIELD_HEADER_V1)

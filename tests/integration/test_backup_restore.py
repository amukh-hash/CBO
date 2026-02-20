from __future__ import annotations

from pathlib import Path

from app.core.backups import BackupManager
from app.core.config import get_settings


def _csrf_headers(client) -> dict[str, str]:
    return {"x-csrf-token": client.cookies.get("cb_csrf", "")}


def _login(client) -> None:
    client.get("/auth/login")
    client.post(
        "/auth/login",
        data={"pin": "1224"},
        headers=_csrf_headers(client),
    )


def test_backup_restore_roundtrip(client, tmp_path: Path) -> None:
    _login(client)
    client.post(
        "/policies/documents/upload",
        files={"file": ("receipt.pdf", b"fake-pdf-2", "application/pdf")},
        data={"doc_type": "receipt"},
        headers=_csrf_headers(client),
    )
    settings = get_settings()
    manager = BackupManager(settings)
    backup = manager.create_backup()
    assert backup.exists()
    restore_dir = tmp_path / "restore"
    manager.restore_to(backup, restore_dir)
    assert (restore_dir / "db.sqlite").exists()
    assert (restore_dir / "documents").exists()

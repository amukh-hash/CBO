from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.config import Settings
from app.core.crypto import KeyManager, encrypt_bytes, decrypt_bytes, CipherBlob


class BackupManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.key_manager = KeyManager()

    def _backup_name(self) -> str:
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"backup-{ts}.cbbak"

    def create_backup(self) -> Path:
        payload_dir = Path(tempfile.mkdtemp(prefix="cb_backup_"))
        raw_zip = payload_dir / "payload.zip"
        with ZipFile(raw_zip, "w", compression=ZIP_DEFLATED) as zf:
            if self.settings.db_path.exists():
                zf.write(self.settings.db_path, arcname="db.sqlite")
            if self.settings.docs_dir.exists():
                for path in sorted(self.settings.docs_dir.rglob("*")):
                    if path.is_file():
                        zf.write(path, arcname=str(Path("documents") / path.relative_to(self.settings.docs_dir)))

        plaintext = raw_zip.read_bytes()
        key = self.key_manager.get_or_create_kek()
        blob = encrypt_bytes(plaintext, key)
        out = self.settings.backup_dir / self._backup_name()
        out.write_bytes(blob.nonce + blob.ciphertext)

        manifest = {
            "file": out.name,
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        (self.settings.backup_dir / f"{out.name}.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        self.enforce_retention(limit=30)
        return out

    def enforce_retention(self, limit: int = 30) -> None:
        backups = sorted(self.settings.backup_dir.glob("backup-*.cbbak"))
        for old in backups[:-limit]:
            old.unlink(missing_ok=True)
            Path(f"{old}.json").unlink(missing_ok=True)

    def restore_to(self, backup_file: Path, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        raw = backup_file.read_bytes()
        blob = CipherBlob(nonce=raw[:12], ciphertext=raw[12:])
        key = self.key_manager.get_or_create_kek()
        plaintext = decrypt_bytes(blob, key)
        restore_zip = target_dir / "restored_payload.zip"
        restore_zip.write_bytes(plaintext)
        with ZipFile(restore_zip, "r") as zf:
            zf.extractall(target_dir)
        return target_dir

    def test_restore(self) -> bool:
        backups = sorted(self.settings.backup_dir.glob("backup-*.cbbak"))
        if not backups:
            return False
        with tempfile.TemporaryDirectory(prefix="cb_restore_test_") as tmp:
            self.restore_to(backups[-1], Path(tmp))
            return True

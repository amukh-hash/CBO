from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_swap(current_bin: Path, new_bin: Path, expected_sha256: str) -> bool:
    if sha256_file(new_bin) != expected_sha256:
        return False
    backup = current_bin.with_suffix(current_bin.suffix + ".rollback")
    shutil.copy2(current_bin, backup)
    try:
        shutil.copy2(new_bin, current_bin)
        return True
    except Exception:
        shutil.copy2(backup, current_bin)
        return False

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _candidate_binaries(base: Path) -> list[Path]:
    names = ["cb-organizer-app", "cb-organizer-app.exe"]
    candidates: list[Path] = []
    for name in names:
        candidates.append(base / name)
        candidates.append(base / "cb-organizer-app" / name)
        candidates.append(base.parent / "cb-organizer-app" / name)
    return candidates


def main() -> None:
    base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    for candidate in _candidate_binaries(base):
        if candidate.exists():
            subprocess.Popen([str(candidate)])
            return
    raise FileNotFoundError("Could not locate cb-organizer-app binary")


if __name__ == "__main__":
    main()

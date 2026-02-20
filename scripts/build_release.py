from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_VENV = ROOT / ".build-venv"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.check_call(cmd, cwd=str(cwd or ROOT))


def _venv_python() -> Path:
    if sys.platform.startswith("win"):
        return BUILD_VENV / "Scripts" / "python.exe"
    return BUILD_VENV / "bin" / "python"


def ensure_build_env() -> Path:
    if not BUILD_VENV.exists():
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(BUILD_VENV)
    py = _venv_python()
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(py), "-m", "pip", "install", "-r", "requirements-build.txt"])
    return py


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest() -> None:
    dist = ROOT / "dist"
    manifest: dict[str, object] = {
        "artifacts": [],
        "python": sys.version,
    }
    artifacts = manifest["artifacts"]
    for artifact in sorted(dist.rglob("*")):
        if artifact.is_file():
            assert isinstance(artifacts, list)
            artifacts.append({"path": str(artifact.relative_to(ROOT)), "sha256": sha256_file(artifact)})
    (ROOT / "dist" / "build-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    py = ensure_build_env()
    run([str(py), "-m", "PyInstaller", "--noconfirm", "scripts/pyinstaller_app.spec"])
    run([str(py), "-m", "PyInstaller", "--noconfirm", "scripts/pyinstaller_launcher.spec"])
    write_manifest()


if __name__ == "__main__":
    main()

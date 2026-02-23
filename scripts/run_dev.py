from __future__ import annotations

import os
import pathlib
import sys
import threading
import time
import webbrowser

# Ensure CWD is the project root so Python resolves 'app' from this project,
# not from a sibling directory that also has an 'app' package.
_PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
os.chdir(_PROJECT_ROOT)
# Insert at position 0 so this project's 'app' package takes absolute priority
sys.path.insert(0, _PROJECT_ROOT)

import uvicorn  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()

    def open_when_ready() -> None:
        time.sleep(1.2)
        webbrowser.open(f"http://{settings.host}:{settings.port}/auth/login")

    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False, access_log=False)


if __name__ == "__main__":
    main()

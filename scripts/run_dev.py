from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()

    def open_when_ready() -> None:
        time.sleep(1.2)
        webbrowser.open(f"http://{settings.host}:{settings.port}/auth/login")

    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False, access_log=False)


if __name__ == "__main__":
    main()

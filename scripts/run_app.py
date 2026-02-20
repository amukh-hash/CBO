from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser

import uvicorn

from app.core.config import get_settings


def _find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def main() -> None:
    settings = get_settings()
    host = settings.host
    port = _find_free_port(host)
    os.environ["CB_HOST"] = host
    os.environ["CB_PORT"] = str(port)

    def open_when_ready() -> None:
        time.sleep(1.2)
        webbrowser.open(f"http://{host}:{port}/auth/login")

    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run("app.main:app", host=host, port=port, reload=False, access_log=False)


if __name__ == "__main__":
    main()

from __future__ import annotations

import httpx


def main() -> None:
    r = httpx.get("http://127.0.0.1:8765/auth/login", timeout=3.0)
    print("OK" if r.status_code == 200 else f"FAIL:{r.status_code}")


if __name__ == "__main__":
    main()

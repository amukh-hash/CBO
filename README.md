# CB Organizer (Local-First Insurance + Medical Expense Organizer)

CB Organizer is an offline-capable Python appliance app for insurance and medical expense tracking.

## Stack
- Python 3.12
- FastAPI + Uvicorn
- SQLAlchemy 2.0 + Alembic
- SQLite (money stored as integer cents)
- Jinja2 + HTMX UI
- Argon2id, AES-256-GCM encryption, keyring support
- APScheduler jobs (backup + integrity checks)
- pytest/httpx/playwright-ready tests
- PyInstaller release build scripts

## Security and Durability Notes
- Localhost-only by default (`CB_LOCALHOST_ONLY=1`), session cookies are restricted for this mode.
- All state-changing routes enforce CSRF using double-submit cookie + header/form token checks.
- Vault encryption uses a durable keystore file at `<data-dir>/config/keystore.json`.
- If OS keyring is unavailable, vault unlock uses passphrase-derived keys (Argon2id).
- During sign-in, the entered 4-digit PIN is used as the vault passphrase in-process.
- Single-user mode is enabled: the default lock PIN is `1224`.
- You can also set `CB_ORGANIZER_PASSPHRASE` explicitly for headless/dev runs.
- Document storage uses per-document DEKs, AES-256-GCM with metadata AAD, and hash verification on read.

## Quick Start (Developer)
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -e .[dev]`
3. `export CB_ORGANIZER_PASSPHRASE='choose-a-strong-passphrase'` (optional if using UI login)
4. `python scripts/run_dev.py`
5. Browser opens at `http://127.0.0.1:8765`

## One-Click End User Flow
1. Build binaries: `python scripts/build_release.py`
2. Distribute launcher executable from `dist/`.
3. User opens launcher and app starts local server + browser UI.
4. Data is stored in local app data folder (override with `CB_DATA_DIR` if needed).

## UI Overview
- **Dashboard**: month calendar with provider-colored appointments, appointment detail popup, and monthly expense + premium totals.
- **Providers**: name, specialty, selector color, estimated co-pay, and notes.
- **Policies & Documents**: policy management plus encrypted PDF/JPEG/PNG storage and inline view.
- **Expenses**: ledger of line items.

## LAN Safety
- To permit non-localhost binding, set `CB_ALLOW_LAN=1` and `CB_LAN_HTTPS_MODE=1`.
- Without both flags, startup refuses non-localhost bind addresses.

## Packaging
- `scripts/build_release.py` uses pinned build dependencies from `requirements-build.txt`.
- PyInstaller specs:
  - `scripts/pyinstaller_app.spec`
  - `scripts/pyinstaller_launcher.spec`

## Tests
Run all tests:
- `pytest`

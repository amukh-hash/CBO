from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    app_name: str = "CB Organizer"
    host: str = field(default_factory=lambda: os.getenv("CB_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("CB_PORT", "8765")))
    localhost_only: bool = field(default_factory=lambda: os.getenv("CB_LOCALHOST_ONLY", "1") == "1")
    allow_lan: bool = field(default_factory=lambda: os.getenv("CB_ALLOW_LAN", "0") == "1")
    lan_https_mode: bool = field(default_factory=lambda: os.getenv("CB_LAN_HTTPS_MODE", "0") == "1")
    secret_key: str = field(default_factory=lambda: os.getenv("CB_SECRET_KEY", "dev-only-secret-change"))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("CB_DATA_DIR", str(Path.home() / ".cb_organizer"))))
    db_name: str = "cb_organizer.db"
    backup_dir_name: str = "backups"
    docs_dir_name: str = "documents"
    config_dir_name: str = "config"
    environment: str = field(default_factory=lambda: os.getenv("CB_ENV", "dev"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name

    @property
    def db_url(self) -> str:
        return f"sqlite+pysqlite:///{self.db_path}"

    @property
    def docs_dir(self) -> Path:
        return self.data_dir / self.docs_dir_name

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / self.backup_dir_name

    @property
    def config_dir(self) -> Path:
        return self.data_dir / self.config_dir_name


def get_settings() -> Settings:
    settings = Settings()
    local_hosts = {"127.0.0.1", "localhost"}

    if settings.allow_lan:
        settings.localhost_only = False

    if settings.localhost_only and settings.host not in local_hosts:
        raise ValueError("Refusing non-localhost bind while CB_LOCALHOST_ONLY=1.")

    if not settings.localhost_only and settings.host not in local_hosts and not settings.allow_lan:
        raise ValueError("Refusing LAN bind unless CB_ALLOW_LAN=1.")

    if not settings.localhost_only and settings.host not in local_hosts and not settings.lan_https_mode:
        raise ValueError("Refusing LAN bind without CB_LAN_HTTPS_MODE=1.")

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    return settings

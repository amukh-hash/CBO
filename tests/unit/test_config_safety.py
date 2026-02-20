from __future__ import annotations

import pytest

from app.core.config import get_settings


def test_refuse_non_localhost_without_allow_lan(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv('CB_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('CB_HOST', '0.0.0.0')
    monkeypatch.setenv('CB_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('CB_ALLOW_LAN', '0')
    with pytest.raises(ValueError):
        get_settings()

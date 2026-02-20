from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="cb_org_tests_"))
os.environ["CB_DATA_DIR"] = str(TEST_DATA_DIR)
os.environ["CB_ORGANIZER_PASSPHRASE"] = "1224"
os.environ["CB_DISABLE_KEYRING"] = "1"
os.environ["CB_LOCALHOST_ONLY"] = "1"


@pytest.fixture()
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as c:
        yield c

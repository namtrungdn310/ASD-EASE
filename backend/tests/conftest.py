import os
os.environ["DATABASE_URL"] = "sqlite:///./test_asd_edge_ai.db"
os.environ["RAW_STORAGE_DIR"] = "./test_raw_storage"

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


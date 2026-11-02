import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory

TEST_HOME = TemporaryDirectory(prefix="asd-ease-unit-")
TEST_ROOT = Path(TEST_HOME.name)
OPERATOR = "operator-unit-" + "x" * 40
TOKEN = "device-unit-" + "y" * 40
OTHER_TOKEN = "device-other-" + "z" * 40
OP_HEADERS = {"Authorization": f"Bearer {OPERATOR}"}
DEVICE_HEADERS = {"Authorization": f"Bearer {TOKEN}"}
registry_path = TEST_ROOT / "registry.json"
registry_path.write_text(json.dumps([
    {"device_id": "SIM-001", "data_origin": "SYNTHETIC", "mqtt_username": "simulator", "http_token": TOKEN, "transport": "http"},
    {"device_id": "SIM-OTHER", "data_origin": "SYNTHETIC", "mqtt_username": "other", "http_token": OTHER_TOKEN, "transport": "http"},
    {"device_id": "ESP-001", "data_origin": "DEVICE", "mqtt_username": "esp", "http_token": "esp-unit-" + "w" * 40, "transport": "mqtt"}
]), encoding="utf-8")
os.environ.update(DATABASE_URL=f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}", RAW_STORAGE_DIR=str(TEST_ROOT / "raw"),
    OPERATOR_TOKEN=OPERATOR, COOKIE_SECRET="cookie-unit-" + "q" * 40, COOKIE_SECURE="false", ALLOW_INSECURE_LOCAL="true",
    DEVICE_REGISTRY_FILE=str(registry_path), MQTT_ENABLED="false")

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine


@pytest.fixture(scope="session", autouse=True)
def release_test_database():
    yield
    engine.dispose()
    TEST_HOME.cleanup()


def sync_payload(boot="BOOT-UNIT", connection="CONN-UNIT", request="REQ-UNIT", **changes):
    return {"control_version": "1.0", "message_type": "STATE_REQUEST", "device_id": "SIM-001", "data_origin": "SYNTHETIC",
        "boot_id": boot, "connection_id": connection, "request_id": request, "actual_state": "IDLE", "session_id": None,
        "last_command_id": None, "last_generation": 0, "timestamp_ms": 0, "last_ack": None} | changes


def start_recording(client, session_id="SYN-SESSION001"):
    result = client.post("/api/v1/sessions/start", headers=OP_HEADERS, json={"device_id": "SIM-001", "session_id": session_id})
    assert result.status_code == 202, result.text
    request = sync_payload(request="REQ-START")
    response = client.post("/api/v1/devices/sync", json=request).json()
    command = response["pending_command"]
    ack = {key: command[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id", "command_id", "generation", "session_id", "action")}
    ack.update(message_type="ACK", result="STARTED", timestamp_ms=0, reason=None, final_summary=None)
    result = client.post("/api/v1/devices/ack", json=ack)
    assert result.status_code == 200, result.text
    return ack


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app, headers=DEVICE_HEADERS) as test_client:
        response = test_client.post("/api/v1/devices/sync", json=sync_payload())
        assert response.status_code == 200, response.text
        yield test_client


@pytest.fixture
def recording(client):
    return start_recording(client)


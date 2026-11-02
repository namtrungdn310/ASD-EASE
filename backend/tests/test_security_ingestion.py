import json
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func
from app.db.database import SessionLocal
from app.db.models import Event, Device
from app.schemas.control import Ack
from app.schemas.ingestion import InboundTelemetry
from conftest import OP_HEADERS, OPERATOR, sync_payload
from test_telemetry import payload


def test_auth_boundaries(client):
    assert client.get("/api/v1/sessions").status_code == 401
    assert client.get("/api/v1/devices", headers={"Authorization": ""}).status_code == 401
    assert client.post("/api/v1/telemetry", json=payload(), headers=OP_HEADERS).status_code == 401
    assert client.post("/api/v1/telemetry", json=payload(), headers={"Authorization": ""}).status_code == 401
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/ws/live", headers={"Authorization": ""}):
            pass


def test_non_ascii_credentials_are_rejected(client):
    assert client.post("/api/v1/auth/login", json={"token": "không-phải-token"}).status_code == 401
    assert client.post("/api/v1/auth/login", content=b'{"token":"\\ud800"}', headers={"Content-Type": "application/json"}).status_code == 401
    assert client.get("/api/v1/sessions", headers=[(b"authorization", b"Bearer \xff")]).status_code == 401


def test_state_sync_is_not_a_fresh_measurement(client):
    devices = client.get("/api/v1/devices", headers=OP_HEADERS).json()
    assert devices[0]["last_seen_at"] is None
    assert client.post("/api/v1/telemetry", json=payload()).status_code == 202
    assert client.get("/api/v1/devices", headers=OP_HEADERS).json()[0]["last_seen_at"] is not None


def test_cookie_login_origin_and_secret_not_in_response(client):
    response = client.post("/api/v1/auth/login", json={"token": OPERATOR}, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200 and OPERATOR not in response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/v1/sessions", headers={"Authorization": ""}).status_code == 200
    body = {"device_id": "SIM-001", "session_id": "CSRF"}
    assert client.post("/api/v1/sessions/start", json=body, headers={"Authorization": "", "Origin": "https://evil.invalid"}).status_code == 401
    assert client.post("/api/v1/sessions/start", json=body, headers={"Authorization": "", "Origin": "http://localhost:5173"}).status_code == 202


def test_wrong_identity_and_source_rejected(client):
    data = payload()
    for changes in ({"device_id": "SIM-OTHER"}, {"data_origin": "DEVICE"}):
        assert client.post("/api/v1/telemetry", json=data | changes).status_code == 403
    assert client.post("/api/v1/sessions/start", json={"device_id": "../OTHER", "session_id": "S"}, headers=OP_HEADERS).status_code == 422
    assert client.post("/api/v1/sessions/start", json={"device_id": "UNREGISTERED", "session_id": "S"}, headers=OP_HEADERS).status_code == 403


@pytest.mark.parametrize("change", [
    {"timestamp_ms": True}, {"timestamp_ms": "1"}, {"timestamp_ms": 1.0},
    {"timestamp_ms": 2**53}, {"hr_bpm": "78"}, {"hr_bpm": False},
    {"signal_quality": {"ppg": 0, "imu": 0, "gsr": 0, "debug": 1}},
    {"gsr": {"raw": 1.0, "delta": None}}, {"gsr": {"raw": 1800, "delta": "0.1"}},
])
def test_strict_telemetry(client, change):
    assert client.post("/api/v1/telemetry", json=payload() | change).status_code == 422


def test_duplicate_does_not_refresh_or_broadcast_twice(client):
    data = payload()
    data["prediction"]["state"] = "UNCERTAIN"
    first = client.post("/api/v1/telemetry", json=data)
    assert first.status_code == 202 and not first.json()["duplicate"]
    with SessionLocal() as db:
        seen = db.get(Device, "SIM-001").last_seen_at
        count = db.scalar(select(func.count()).select_from(Event))
    second = client.post("/api/v1/telemetry", json=data)
    assert second.status_code == 202 and second.json()["duplicate"]
    with SessionLocal() as db:
        assert db.get(Device, "SIM-001").last_seen_at == seen
        assert db.scalar(select(func.count()).select_from(Event)) == count
    assert client.post("/api/v1/telemetry", json=data | {"hr_bpm": 80}).status_code == 409


def test_wire_rejects_duplicates_nonfinite_depth_and_chunked_oversize(client):
    assert client.post("/api/v1/telemetry", content=b'{"x":1,"x":2}', headers={"Content-Type": "application/json"}).status_code == 400
    assert client.post("/api/v1/telemetry", content=b'{"x":NaN}', headers={"Content-Type": "application/json"}).status_code == 400
    assert client.post("/api/v1/telemetry", content=b'{}', headers={"Content-Type": "text/plain"}).status_code == 415
    def chunks():
        yield b"{" + b" " * 4096
        yield b"}"
    assert client.post("/api/v1/telemetry", content=chunks(), headers={"Content-Type": "application/json"}).status_code == 413


def test_telemetry_session_requires_ack_and_ownership(client):
    data = payload() | {"session_id": "NEW"}
    assert client.post("/api/v1/telemetry", json=data).status_code == 404
    client.post("/api/v1/sessions/start", json={"device_id": "SIM-001", "session_id": "NEW"}, headers=OP_HEADERS)
    assert client.post("/api/v1/telemetry", json=data).status_code == 409


def test_new_backend_needs_resynchronization(client):
    from app.main import app
    app.state.mqtt.live.clear()
    assert client.post("/api/v1/telemetry", json=payload()).status_code == 409
    assert client.post("/api/v1/devices/sync", json=sync_payload(request="AFTER-RESTART")).status_code == 200
    assert client.post("/api/v1/telemetry", json=payload()).status_code == 202


def test_bounded_queue_retained_and_old_presence(client):
    import asyncio
    from app.main import app
    runtime = app.state.mqtt
    runtime.settings.mqtt_queue_messages = 1
    while runtime.enqueue("a", b"{}"):
        pass
    assert runtime.counters["overload"] >= 1
    assert not runtime.enqueue("a", b"x" * 4097)
    assert runtime.counters["oversize"] == 1
    prefix = "asd-ease/v1/SYNTHETIC/SIM-001/"
    with pytest.raises(HTTPException):
        asyncio.run(runtime.process(prefix + "state/request", json.dumps(sync_payload()).encode(), True))


def test_contract_control_fixtures_match_runtime_schema():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "docs" / "contracts"))
    from check_examples import load_catalog
    from app.schemas.control import Ack, Command, Presence, StateRequest, StateResponse
    catalog, resolved = load_catalog()
    models = {"ACK": Ack, "COMMAND": Command, "PRESENCE": Presence, "STATE_REQUEST": StateRequest, "STATE_RESPONSE": StateResponse}
    for example in catalog["examples"]:
        if example["kind"] == "control":
            data = resolved[example["id"]]
            assert models[data["message_type"]].model_validate(data)

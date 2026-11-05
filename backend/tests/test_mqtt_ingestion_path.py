"""Hồi quy đường MQTT thật của backend: phiên, DB, WebSocket và quyền nhận."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.db.database import SessionLocal
from app.db.models import Device
from app.services.websocket_manager import manager
from conftest import OPERATOR, sync_payload
from test_telemetry import payload


PREFIX = "asd-ease/v1/DEVICE/ESP-001/"


def device_payload():
    return {
        "schema_version": "1.0", "device_id": "ESP-001", "session_id": None,
        "timestamp_ms": 1000, "data_origin": "DEVICE", "hr_bpm": None,
        "gsr": {"raw": 1810, "delta": None}, "movement": {"score": None},
        "signal_quality": {"ppg": 0, "gsr": 0, "imu": 0},
        "prediction": {"probability": None, "state": "UNCERTAIN"},
        "firmware_version": "0.2.0", "model_version": "none",
    }


def synchronize_device(runtime):
    from app.schemas.control import StateRequest
    identity = app.state.registry.identity("ESP-001", "DEVICE")
    request = StateRequest.model_validate(sync_payload(device_id="ESP-001", data_origin="DEVICE"))
    runtime.sync(identity, request)


@pytest.mark.parametrize("suffix", ["sensors/ppg", "sensors/imu", "sensors/gsr", "ppg", "imu", "gsr"])
def test_sensor_topics_cannot_bypass_ingestion_or_broadcast(client, monkeypatch, suffix):
    broadcast = AsyncMock()
    monkeypatch.setattr(manager, "broadcast", broadcast)
    with pytest.raises(HTTPException) as error:
        asyncio.run(app.state.mqtt.process(PREFIX + suffix, json.dumps(device_payload()).encode(), False))
    assert error.value.status_code == 403
    assert error.value.detail == "TOPIC_NOT_ALLOWED"
    broadcast.assert_not_called()


def test_mqtt_subscribes_only_to_four_registered_inbound_channels(client):
    transport = Mock()
    app.state.mqtt._connected(transport, None, None, SimpleNamespace(is_failure=False), None)
    transport.subscribe.assert_called_once_with([
        (PREFIX + "telemetry", 0), (PREFIX + "ack", 1),
        (PREFIX + "state/request", 1), (PREFIX + "presence", 1),
    ])


def test_only_synchronized_measurements_reach_db_and_websocket(client, monkeypatch):
    runtime = app.state.mqtt
    broadcast = AsyncMock()
    monkeypatch.setattr(manager, "broadcast", broadcast)
    wire = json.dumps(device_payload()).encode()
    with pytest.raises(HTTPException) as error:
        asyncio.run(runtime.process(PREFIX + "telemetry", wire, False))
    assert error.value.status_code == 409
    broadcast.assert_not_called()
    synchronize_device(runtime)
    asyncio.run(runtime.process(PREFIX + "telemetry", wire, False))
    broadcast.assert_awaited_once_with(device_payload())
    with SessionLocal() as db:
        assert db.get(Device, "ESP-001").last_telemetry_at is not None
    asyncio.run(runtime.process(PREFIX + "telemetry", wire, False))
    assert broadcast.await_count == 1  # Gửi lặp không làm Dashboard tươi trở lại.
    stale = device_payload() | {"timestamp_ms": 999}
    with pytest.raises(HTTPException) as error:
        asyncio.run(runtime.process(PREFIX + "telemetry", json.dumps(stale).encode(), False))
    assert error.value.status_code == 409
    assert broadcast.await_count == 1


def test_database_failure_never_broadcasts_success(client, monkeypatch):
    runtime = app.state.mqtt
    synchronize_device(runtime)
    broadcast = AsyncMock()
    monkeypatch.setattr(manager, "broadcast", broadcast)

    def fail_commit(*args, **kwargs):
        raise OperationalError("commit failed", {}, None)

    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "commit", fail_commit)
    with pytest.raises(HTTPException) as error:
        asyncio.run(runtime.process(PREFIX + "telemetry", json.dumps(device_payload()).encode(), False))
    assert error.value.status_code == 503
    assert error.value.detail == "STORAGE_UNAVAILABLE"
    broadcast.assert_not_called()


def test_local_origin_does_not_replace_operator_login(client):
    headers = {"Authorization": "", "Origin": "http://localhost:5173"}
    assert client.get("/api/v1/sessions", headers=headers).status_code == 401
    assert client.get(f"/api/v1/sessions?token={OPERATOR}", headers=headers).status_code == 401
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/api/v1/ws/live?token={OPERATOR}", headers=headers):
            pass
    assert error.value.code == 1008


def test_browser_cookie_authenticates_websocket_without_token_in_url(client):
    response = client.post("/api/v1/auth/login", json={"token": OPERATOR},
                           headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    headers = {"Authorization": "", "Origin": "http://localhost:5173"}
    with client.websocket_connect("/api/v1/ws/live", headers=headers) as socket:
        assert client.post("/api/v1/telemetry", json=payload()).status_code == 202
        assert socket.receive_json() == payload()

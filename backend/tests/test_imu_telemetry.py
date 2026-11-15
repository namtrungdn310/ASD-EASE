"""Telemetry1.1 đi qua chung schema/nghiệp vụ MQTT/HTTP và WebSocket."""
import asyncio
from copy import deepcopy
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from app.main import app
from app.schemas.ingestion import InboundTelemetry
from app.services.websocket_manager import manager
from conftest import OP_HEADERS
from test_telemetry import payload
from test_mqtt_ingestion_path import PREFIX, device_payload, synchronize_device


def axes_payload(base=None):
    frame = deepcopy(base if base is not None else payload())
    frame["schema_version"] = "1.1"
    frame["movement"].update(acceleration={"x": -0.5, "y": 0, "z": 9.806},
                             angular_velocity={"x": -90, "y": 0, "z": 20.5})
    return frame


def test_imu_http_to_websocket_keeps_six_axes_and_units(client):
    frame = axes_payload()
    with client.websocket_connect("/api/v1/ws/live", headers=OP_HEADERS) as socket:
        assert client.post("/api/v1/telemetry", json=frame).status_code == 202
        assert socket.receive_json() == frame
    stored = InboundTelemetry.model_validate(frame).telemetry()
    assert stored.schema_version == "1.1"
    assert stored.movement.acceleration.z == 9.806
    assert stored.movement.angular_velocity.x == -90


def test_imu_mqtt_uses_same_receiver_and_duplicates_are_not_broadcast(client, monkeypatch):
    synchronize_device(app.state.mqtt)
    broadcast = AsyncMock()
    monkeypatch.setattr(manager, "broadcast", broadcast)
    frame = axes_payload(device_payload())
    asyncio.run(app.state.mqtt.process(PREFIX + "telemetry", json.dumps(frame).encode(), False))
    broadcast.assert_awaited_once_with(frame)
    frame["movement"]["angular_velocity"]["x"] = -90.0
    asyncio.run(app.state.mqtt.process(PREFIX + "telemetry", json.dumps(frame).encode(), False))
    assert broadcast.await_count == 1  # Số nguyên/số thực cùng giá trị vẫn là gói trùng.


@pytest.mark.parametrize("value", [None, {"x": 0, "y": 0, "z": 0}])
def test_imu_preserves_null_or_real_zero(client, value):
    frame = axes_payload()
    frame["movement"].update(acceleration=value, angular_velocity=value)
    assert client.post("/api/v1/telemetry", json=frame).status_code == 202
    result = InboundTelemetry.model_validate(frame).model_dump()
    assert result["movement"]["acceleration"] == value
    assert result["movement"]["angular_velocity"] == value


@pytest.mark.parametrize("key", ["acceleration", "angular_velocity"])
@pytest.mark.parametrize("value", [{}, [], {"x": 1, "y": 2}, {"x": None, "y": 0, "z": 0},
                                   {"x": True, "y": 0, "z": 0}, {"x": "1", "y": 0, "z": 0},
                                   {"x": 1, "y": 2, "z": 3, "unit": "g"}])
def test_imu_rejects_partial_coerced_or_unknown_axes(client, key, value):
    frame = axes_payload()
    frame["movement"][key] = value
    assert client.post("/api/v1/telemetry", json=frame).status_code == 422


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_imu_rejects_non_finite_numbers(value):
    frame = axes_payload()
    frame["movement"]["acceleration"]["x"] = value
    with pytest.raises(ValidationError):
        InboundTelemetry.model_validate(frame)


def test_imu_version_boundary_keeps_legacy_shape(client):
    legacy = InboundTelemetry.model_validate(payload())
    assert legacy.model_dump()["movement"] == {"score": 0.2}
    assert legacy.telemetry().schema_version == "1.0"
    for version in ("1.0", "1.2", "2.0"):
        frame = axes_payload()
        frame["schema_version"] = version
        assert client.post("/api/v1/telemetry", json=frame).status_code == 422
    for key in ("acceleration", "angular_velocity"):
        frame = axes_payload()
        del frame["movement"][key]
        assert client.post("/api/v1/telemetry", json=frame).status_code == 422

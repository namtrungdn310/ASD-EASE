"""Điểm 1.2 đi nguyên vẹn qua receiver, không làm thay đổi các bản cũ."""
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
from test_imu_telemetry import axes_payload
from test_mqtt_ingestion_path import PREFIX, device_payload, synchronize_device


def quality_payload(base=None):
    frame = axes_payload(base)
    frame["schema_version"] = "1.2"
    frame["signal_quality"] = {
        "method": "engineering-v1", "window_ms": 8000,
        "hr": {"score": .32, "reason": "weak_signal"},
        "gsr": {"score": 1, "reason": "ok"},
        "acceleration": {"score": .95, "reason": "saturated"},
        "rotation": {"score": None, "reason": "calibrating"},
    }
    return frame


def test_quality_http_to_websocket_keeps_score_zero_and_null(client):
    frame = quality_payload()
    frame["signal_quality"]["hr"] = {"score": 0, "reason": "no_contact"}
    with client.websocket_connect("/api/v1/ws/live", headers=OP_HEADERS) as ws:
        assert client.post("/api/v1/telemetry", json=frame).status_code == 202
        assert ws.receive_json() == frame
    assert InboundTelemetry.model_validate(frame).telemetry().signal_quality.rotation.score is None


def test_quality_mqtt_uses_shared_receiver(client, monkeypatch):
    synchronize_device(app.state.mqtt)
    broadcast = AsyncMock()
    monkeypatch.setattr(manager, "broadcast", broadcast)
    frame = quality_payload(device_payload())
    frame["signal_quality"]["hr"]["sample_count"] = 397
    asyncio.run(app.state.mqtt.process(PREFIX + "telemetry", json.dumps(frame).encode(), False))
    broadcast.assert_awaited_once_with(frame)
    asyncio.run(app.state.mqtt.process(PREFIX + "telemetry", json.dumps(frame).encode(), False))
    assert broadcast.await_count == 1


def test_sensor_counts_survive_http_to_websocket(client):
    frame = quality_payload()
    for name, count in {"hr": 397, "gsr": 159, "acceleration": 400, "rotation": 400}.items():
        frame["signal_quality"][name]["sample_count"] = count
    with client.websocket_connect("/api/v1/ws/live", headers=OP_HEADERS) as ws:
        assert client.post("/api/v1/telemetry", json=frame).status_code == 202
        assert ws.receive_json() == frame


@pytest.mark.parametrize("count", [-1, True, "400", 1.5, 9007199254740992])
def test_rejects_invalid_sensor_counts(count):
    frame = quality_payload()
    frame["signal_quality"]["hr"]["sample_count"] = count
    with pytest.raises(ValidationError):
        InboundTelemetry.model_validate(frame)


@pytest.mark.parametrize("score", [-.1, 1.1, True, "0.9", float("nan"), float("inf")])
def test_rejects_invalid_scores(score):
    frame = quality_payload()
    frame["signal_quality"]["hr"]["score"] = score
    with pytest.raises(ValidationError):
        InboundTelemetry.model_validate(frame)


@pytest.mark.parametrize("change", [
    {"hr": {"score": None, "reason": "ok"}},
    {"hr": {"score": .9, "reason": "stale"}},
    {"hr": {"score": .9, "reason": "unknown"}},
    {"hr": {"score": .9, "reason": "ok", "confidence": 1}},
    {"method": "accuracy"}, {"window_ms": 5000},
])
def test_rejects_unversioned_or_ambiguous_quality(change):
    frame = quality_payload()
    frame["signal_quality"].update(deepcopy(change))
    with pytest.raises(ValidationError):
        InboundTelemetry.model_validate(frame)


def test_version_boundary_requires_new_shape_only_in_v12():
    for version in ("1.0", "1.1"):
        frame = quality_payload()
        frame["schema_version"] = version
        with pytest.raises(ValidationError):
            InboundTelemetry.model_validate(frame)
    frame = axes_payload()
    frame["schema_version"] = "1.2"
    with pytest.raises(ValidationError):
        InboundTelemetry.model_validate(frame)


def test_quality_method_versions():
    from app.schemas.quality import MetricQuality
    from pydantic import ValidationError
    import pytest
    data = {"window_ms": 8000, **{name: {"score": .75, "reason": "ok"}
            for name in ("hr", "gsr", "acceleration", "rotation")}}
    for method in ("engineering-v1", "engineering-v2"):
        assert MetricQuality.model_validate({**data, "method": method}).method == method
    with pytest.raises(ValidationError):
        MetricQuality.model_validate({**data, "method": "engineering-v3"})

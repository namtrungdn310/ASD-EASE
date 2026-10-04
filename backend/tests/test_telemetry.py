import pytest
from app.core.enums import EngineeringState


def payload():
    return {
        "schema_version": "1.0", "device_id": "SIM-001", "session_id": "SYN-SESSION001",
        "timestamp_ms": 1000, "data_origin": "SYNTHETIC", "hr_bpm": 78.4,
        "gsr": {"raw": 1810, "delta": 0.04}, "movement": {"score": 0.2},
        "signal_quality": {"ppg": 0.9, "gsr": 0.85, "imu": 1.0},
        "prediction": {"probability": 0.3, "state": "NORMAL"},
        "firmware_version": "simulator-0.1.0", "model_version": "synthetic-rules-none"
    }


def test_valid_telemetry(client):
    assert client.post("/api/v1/telemetry", json=payload()).status_code == 202


def test_invalid_telemetry(client):
    data = payload(); data["hr_bpm"] = "fast"
    assert client.post("/api/v1/telemetry", json=data).status_code == 422


def test_signal_quality_bounds(client):
    data = payload(); data["signal_quality"]["ppg"] = 1.1
    assert client.post("/api/v1/telemetry", json=data).status_code == 422


@pytest.mark.parametrize("state", [item.value for item in EngineeringState])
def test_state_enum(client, state):
    data = payload(); data["prediction"]["state"] = state
    assert client.post("/api/v1/telemetry", json=data).status_code == 202


def test_unknown_state_rejected(client):
    data = payload(); data["prediction"]["state"] = "ANXIETY"
    assert client.post("/api/v1/telemetry", json=data).status_code == 422


def test_websocket_broadcast(client):
    with client.websocket_connect("/api/v1/ws/live") as socket:
        response = client.post("/api/v1/telemetry", json=payload())
        assert response.status_code == 202
        assert socket.receive_json()["data_origin"] == "SYNTHETIC"


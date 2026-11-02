"""Tests for the MQTT subscriber service.

These tests use mocking — they do NOT require a running MQTT broker.
They verify:
  - Unified payload → persist + WebSocket broadcast
  - 3 Sensor-specific topics (PPG, GSR, IMU) → aggregated + WebSocket broadcast
  - Sequential sensor updates accumulate correctly
  - Invalid JSON / schema / topic → no broadcast, backend stays alive
  - device_id mismatch between topic and payload → dropped
  - Lifecycle start/stop
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mqtt_subscriber import (
    MqttSubscriber,
    SENSOR_TOPIC_REGEX,
    UNIFIED_TOPIC_REGEX,
    TOPIC_REGEX,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _valid_payload() -> dict:
    return {
        "schema_version": "1.0",
        "device_id": "ESP32-001",
        "session_id": None,
        "timestamp_ms": 5000,
        "data_origin": "DEVICE",
        "hr_bpm": None,
        "gsr": {"raw": 2048, "delta": None},
        "movement": {"score": None},
        "signal_quality": {"ppg": 0.5, "gsr": 0.4, "imu": 1.0},
        "prediction": {"probability": None, "state": "UNCERTAIN"},
        "firmware_version": "0.2.0",
        "model_version": "none",
    }


def _make_message(topic: str, payload: dict | str | bytes):
    """Create a minimal mock aiomqtt.Message."""
    msg = MagicMock()
    msg.topic = MagicMock()
    msg.topic.__str__ = MagicMock(return_value=topic)
    if isinstance(payload, dict):
        msg.payload = json.dumps(payload).encode()
    elif isinstance(payload, str):
        msg.payload = payload.encode()
    else:
        msg.payload = payload
    return msg


# ---------------------------------------------------------------------------
# Topic regex tests
# ---------------------------------------------------------------------------
class TestTopicRegex:
    def test_valid_unified_topic(self):
        assert UNIFIED_TOPIC_REGEX.match("asd/v1/devices/ESP32-001/telemetry")
        assert TOPIC_REGEX.match("asd/v1/devices/ESP32-001/telemetry")

    def test_valid_sensor_topics(self):
        for sensor in ("ppg", "gsr", "imu", "PPG", "GSR", "IMU"):
            match = SENSOR_TOPIC_REGEX.match(f"asd/v1/devices/ESP32-001/sensors/{sensor}")
            assert match is not None
            assert match.group(1) == "ESP32-001"
            assert match.group(2).lower() == sensor.lower()

            # telemetry/sensor format
            match2 = SENSOR_TOPIC_REGEX.match(f"asd/v1/devices/ESP32-001/telemetry/{sensor}")
            assert match2 is not None

            # direct sensor format
            match3 = SENSOR_TOPIC_REGEX.match(f"asd/v1/devices/ESP32-001/{sensor}")
            assert match3 is not None

    def test_reject_invalid_topics(self):
        assert UNIFIED_TOPIC_REGEX.match("asd/v1/devices//telemetry") is None
        assert UNIFIED_TOPIC_REGEX.match("other/topic") is None
        assert SENSOR_TOPIC_REGEX.match("asd/v1/devices/ESP32-001/sensors/camera") is None


# ---------------------------------------------------------------------------
# Individual sensor topics handling & aggregation
# ---------------------------------------------------------------------------
class TestSensorTopicsHandling:
    @pytest.mark.asyncio
    async def test_ppg_sensor_broadcast(self):
        sub = MqttSubscriber()
        payload = {
            "schema_version": "1.0",
            "device_id": "ESP32-001",
            "timestamp_ms": 1000,
            "sensor": "ppg",
            "status": "VALID",
            "hr_bpm": 76.5,
            "signal_quality": 0.9,
        }
        msg = _make_message("asd/v1/devices/ESP32-001/sensors/ppg", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast, \
             patch("app.services.mqtt_subscriber.persist_telemetry") as mock_persist, \
             patch("app.services.mqtt_subscriber.SessionLocal"):
            await sub._handle_message(msg)

            assert mock_bcast.call_count == 1
            bcast_data = mock_bcast.call_args[0][0]
            assert bcast_data["device_id"] == "ESP32-001"
            assert bcast_data["hr_bpm"] == 76.5
            assert bcast_data["signal_quality"]["ppg"] == 0.9
            assert mock_persist.call_count == 1

    @pytest.mark.asyncio
    async def test_gsr_sensor_broadcast(self):
        sub = MqttSubscriber()
        payload = {
            "schema_version": "1.0",
            "device_id": "ESP32-001",
            "timestamp_ms": 2000,
            "sensor": "gsr",
            "status": "VALID",
            "raw": 1950,
            "delta": 0.12,
            "signal_quality": 0.85,
        }
        msg = _make_message("asd/v1/devices/ESP32-001/sensors/gsr", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast, \
             patch("app.services.mqtt_subscriber.persist_telemetry"), \
             patch("app.services.mqtt_subscriber.SessionLocal"):
            await sub._handle_message(msg)

            assert mock_bcast.call_count == 1
            bcast_data = mock_bcast.call_args[0][0]
            assert bcast_data["gsr"]["raw"] == 1950
            assert bcast_data["gsr"]["delta"] == 0.12
            assert bcast_data["signal_quality"]["gsr"] == 0.85

    @pytest.mark.asyncio
    async def test_imu_sensor_broadcast(self):
        sub = MqttSubscriber()
        payload = {
            "schema_version": "1.0",
            "device_id": "ESP32-001",
            "timestamp_ms": 3000,
            "sensor": "imu",
            "status": "VALID",
            "movement_score": 0.35,
            "signal_quality": 1.0,
        }
        msg = _make_message("asd/v1/devices/ESP32-001/sensors/imu", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast, \
             patch("app.services.mqtt_subscriber.persist_telemetry"), \
             patch("app.services.mqtt_subscriber.SessionLocal"):
            await sub._handle_message(msg)

            assert mock_bcast.call_count == 1
            bcast_data = mock_bcast.call_args[0][0]
            assert bcast_data["movement"]["score"] == 0.35
            assert bcast_data["signal_quality"]["imu"] == 1.0

    @pytest.mark.asyncio
    async def test_sequential_3_sensors_aggregation(self):
        """Publish PPG, GSR, and IMU in sequence — verify data is aggregated into complete frame."""
        sub = MqttSubscriber()

        ppg_msg = _make_message("asd/v1/devices/ESP32-001/sensors/ppg", {
            "device_id": "ESP32-001",
            "timestamp_ms": 100,
            "sensor": "ppg",
            "status": "VALID",
            "hr_bpm": 80.0,
            "signal_quality": 0.9,
        })
        gsr_msg = _make_message("asd/v1/devices/ESP32-001/sensors/gsr", {
            "device_id": "ESP32-001",
            "timestamp_ms": 105,
            "sensor": "gsr",
            "status": "VALID",
            "raw": 2100,
            "delta": 0.08,
            "signal_quality": 0.88,
        })
        imu_msg = _make_message("asd/v1/devices/ESP32-001/sensors/imu", {
            "device_id": "ESP32-001",
            "timestamp_ms": 110,
            "sensor": "imu",
            "status": "VALID",
            "score": 0.2,
            "signal_quality": 1.0,
        })

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast, \
             patch("app.services.mqtt_subscriber.persist_telemetry"), \
             patch("app.services.mqtt_subscriber.SessionLocal"):
            await sub._handle_message(ppg_msg)
            await sub._handle_message(gsr_msg)
            await sub._handle_message(imu_msg)

            assert mock_bcast.call_count == 3
            # Third broadcast must contain accumulated data from all 3 sensors
            last_call = mock_bcast.call_args_list[2][0][0]
            assert last_call["hr_bpm"] == 80.0
            assert last_call["gsr"]["raw"] == 2100
            assert last_call["gsr"]["delta"] == 0.08
            assert last_call["movement"]["score"] == 0.2
            assert last_call["signal_quality"]["ppg"] == 0.9
            assert last_call["signal_quality"]["gsr"] == 0.88
            assert last_call["signal_quality"]["imu"] == 1.0

    @pytest.mark.asyncio
    async def test_sensor_device_id_mismatch_dropped(self):
        sub = MqttSubscriber()
        payload = {
            "device_id": "WRONG-ID",
            "timestamp_ms": 1000,
            "sensor": "ppg",
            "hr_bpm": 70.0,
        }
        msg = _make_message("asd/v1/devices/ESP32-001/sensors/ppg", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast, \
             patch("app.services.mqtt_subscriber.persist_telemetry") as mock_persist, \
             patch("app.services.mqtt_subscriber.SessionLocal"):
            await sub._handle_message(msg)

            assert mock_bcast.call_count == 0
            assert mock_persist.call_count == 0


# ---------------------------------------------------------------------------
# Message handling tests (Unified payload)
# ---------------------------------------------------------------------------
class TestHandleUnifiedMessage:
    @pytest.mark.asyncio
    async def test_valid_payload_persisted_and_broadcast(self):
        sub = MqttSubscriber()
        payload = _valid_payload()
        msg = _make_message("asd/v1/devices/ESP32-001/telemetry", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast, \
             patch("app.services.mqtt_subscriber.persist_telemetry") as mock_persist, \
             patch("app.services.mqtt_subscriber.SessionLocal"):

            await sub._handle_message(msg)

            assert mock_persist.call_count == 1
            assert mock_bcast.call_count == 1

            broadcast_arg = mock_bcast.call_args[0][0]
            assert broadcast_arg["device_id"] == "ESP32-001"
            assert broadcast_arg["schema_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_invalid_json_dropped(self):
        sub = MqttSubscriber()
        msg = _make_message("asd/v1/devices/ESP32-001/telemetry", "not-json{")

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast:
            await sub._handle_message(msg)
            assert mock_bcast.call_count == 0

    @pytest.mark.asyncio
    async def test_schema_validation_failure_dropped(self):
        sub = MqttSubscriber()
        bad_payload = {"device_id": "ESP32-001", "missing": "almost_everything"}
        msg = _make_message("asd/v1/devices/ESP32-001/telemetry", bad_payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast:
            await sub._handle_message(msg)
            assert mock_bcast.call_count == 0

    @pytest.mark.asyncio
    async def test_device_id_mismatch_dropped(self):
        sub = MqttSubscriber()
        payload = _valid_payload()
        payload["device_id"] = "OTHER-DEVICE"
        msg = _make_message("asd/v1/devices/ESP32-001/telemetry", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast:
            await sub._handle_message(msg)
            assert mock_bcast.call_count == 0

    @pytest.mark.asyncio
    async def test_unexpected_topic_dropped(self):
        sub = MqttSubscriber()
        payload = _valid_payload()
        msg = _make_message("asd/v1/devices/ESP32-001/unknown_subtopic", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast:
            await sub._handle_message(msg)
            assert mock_bcast.call_count == 0

    @pytest.mark.asyncio
    async def test_persist_failure_does_not_block_broadcast(self):
        sub = MqttSubscriber()
        payload = _valid_payload()
        msg = _make_message("asd/v1/devices/ESP32-001/telemetry", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast, \
             patch("app.services.mqtt_subscriber.persist_telemetry", side_effect=RuntimeError("DB boom")), \
             patch("app.services.mqtt_subscriber.SessionLocal"):

            await sub._handle_message(msg)
            assert mock_bcast.call_count == 1

    @pytest.mark.asyncio
    async def test_extra_fields_in_payload_rejected_by_schema(self):
        sub = MqttSubscriber()
        payload = _valid_payload()
        payload["unexpected_field"] = "bad"
        msg = _make_message("asd/v1/devices/ESP32-001/telemetry", payload)

        with patch("app.services.mqtt_subscriber.manager.broadcast", new_callable=AsyncMock) as mock_bcast:
            await sub._handle_message(msg)
            assert mock_bcast.call_count == 0


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------
class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        sub = MqttSubscriber()
        with patch.object(sub, "_run_loop", return_value=asyncio.sleep(100)):
            await sub.start()
            assert sub._task is not None
            assert not sub._task.done()

            # Second start is idempotent
            await sub.start()

            await sub.stop()
            assert sub._task is None

    @pytest.mark.asyncio
    async def test_stop_cancels_cleanly(self):
        sub = MqttSubscriber()
        with patch.object(sub, "_run_loop", side_effect=asyncio.CancelledError):
            await sub.start()
            await sub.stop()
            assert sub._task is None

    @pytest.mark.asyncio
    async def test_stop_when_not_started_is_noop(self):
        sub = MqttSubscriber()
        await sub.stop()  # Should not raise

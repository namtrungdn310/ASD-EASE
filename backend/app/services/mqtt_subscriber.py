"""MQTT subscriber for live telemetry ingestion.

Connects to the MQTT broker, subscribes to device telemetry topics, validates
payloads, aggregates sensor-specific topics into complete Telemetry frames,
persists via the database service, and broadcasts via WebSocket.

Supported MQTT Topic Patterns:
  - asd/v1/devices/{device_id}/sensors/{sensor_type}   (sensor_type: ppg, gsr, imu)
  - asd/v1/devices/{device_id}/telemetry/{sensor_type} (sensor_type: ppg, gsr, imu)
  - asd/v1/devices/{device_id}/telemetry               (unified full frame)

Lifecycle: started on FastAPI startup, stopped cleanly on shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import aiomqtt

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.schemas.telemetry import Telemetry
from app.services.telemetry_service import persist_telemetry
from app.services.websocket_manager import manager

logger = logging.getLogger("asd.mqtt")

# Topic patterns
TOPIC_FILTER = "asd/v1/devices/#"

UNIFIED_TOPIC_REGEX = re.compile(r"^asd/v1/devices/([A-Za-z0-9_\-]{1,64})/telemetry$")
SENSOR_TOPIC_REGEX = re.compile(
    r"^asd/v1/devices/([A-Za-z0-9_\-]{1,64})/(?:sensors/|telemetry/)?(ppg|gsr|imu)$",
    re.IGNORECASE,
)

# Alias for backwards compatibility with tests
TOPIC_REGEX = UNIFIED_TOPIC_REGEX

# QoS 1 — at-least-once delivery.
QOS = 1

# Reconnect backoff limits (seconds)
_RECONNECT_MIN_S = 1
_RECONNECT_MAX_S = 30


class DeviceTelemetryAggregator:
    """Aggregates individual sensor telemetry messages into a complete Telemetry frame."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.session_id: str | None = None
        self.timestamp_ms: int = 0
        self.data_origin: str = "DEVICE"
        self.hr_bpm: float | None = None
        self.gsr_raw: int | None = None
        self.gsr_delta: float | None = None
        self.movement_score: float | None = None
        self.sq_ppg: float = 0.0
        self.sq_gsr: float = 0.0
        self.sq_imu: float = 0.0
        self.ppg_status: str = "DISCONNECTED"
        self.gsr_status: str = "DISCONNECTED"
        self.imu_status: str = "DISCONNECTED"
        self.pred_state: str = "UNCERTAIN"
        self.pred_prob: float | None = None
        self.firmware_version: str = "0.2.0"
        self.model_version: str = "none"

    def _update_common(self, payload: dict[str, Any]) -> None:
        if "session_id" in payload:
            self.session_id = payload["session_id"]
        if "timestamp_ms" in payload and isinstance(payload["timestamp_ms"], (int, float)):
            self.timestamp_ms = int(payload["timestamp_ms"])
        if "data_origin" in payload and payload["data_origin"] in ("DEVICE", "SYNTHETIC"):
            self.data_origin = payload["data_origin"]
        if "firmware_version" in payload and isinstance(payload["firmware_version"], str):
            self.firmware_version = payload["firmware_version"]

    def update_unified(self, telemetry: Telemetry) -> None:
        self.session_id = telemetry.session_id
        self.timestamp_ms = telemetry.timestamp_ms
        self.data_origin = telemetry.data_origin
        self.hr_bpm = telemetry.hr_bpm
        self.gsr_raw = telemetry.gsr.raw
        self.gsr_delta = telemetry.gsr.delta
        self.movement_score = telemetry.movement.score
        self.sq_ppg = telemetry.signal_quality.ppg
        self.sq_gsr = telemetry.signal_quality.gsr
        self.sq_imu = telemetry.signal_quality.imu
        self.pred_prob = telemetry.prediction.probability
        self.pred_state = telemetry.prediction.state
        self.firmware_version = telemetry.firmware_version
        self.model_version = telemetry.model_version

    def update_ppg(self, payload: dict[str, Any]) -> None:
        self._update_common(payload)
        self.ppg_status = str(payload.get("status", "VALID"))

        hr = payload.get("hr_bpm")
        if hr is not None and isinstance(hr, (int, float)) and 20.0 <= hr <= 240.0:
            self.hr_bpm = round(float(hr), 1)
        else:
            self.hr_bpm = None

        sq = payload.get("signal_quality")
        if sq is not None and isinstance(sq, (int, float)):
            self.sq_ppg = max(0.0, min(1.0, float(sq)))

    def update_gsr(self, payload: dict[str, Any]) -> None:
        self._update_common(payload)
        self.gsr_status = str(payload.get("status", "VALID"))

        raw = payload.get("raw")
        if raw is not None and isinstance(raw, int) and 0 <= raw <= 4095:
            self.gsr_raw = raw
        else:
            self.gsr_raw = None

        delta = payload.get("delta")
        if delta is not None and isinstance(delta, (int, float)):
            self.gsr_delta = float(delta)
        else:
            self.gsr_delta = None

        sq = payload.get("signal_quality")
        if sq is not None and isinstance(sq, (int, float)):
            self.sq_gsr = max(0.0, min(1.0, float(sq)))

    def update_imu(self, payload: dict[str, Any]) -> None:
        self._update_common(payload)
        self.imu_status = str(payload.get("status", "VALID"))

        score = payload.get("movement_score", payload.get("score"))
        if score is not None and isinstance(score, (int, float)):
            self.movement_score = max(0.0, min(1.0, float(score)))
        else:
            self.movement_score = None

        sq = payload.get("signal_quality")
        if sq is not None and isinstance(sq, (int, float)):
            self.sq_imu = max(0.0, min(1.0, float(sq)))

    def _derive_prediction_state(self) -> str:
        if (
            self.ppg_status == "CALIBRATING"
            or self.gsr_status == "CALIBRATING"
            or self.imu_status == "CALIBRATING"
        ):
            return "CALIBRATING"
        return "UNCERTAIN"

    def to_telemetry(self) -> Telemetry:
        return Telemetry.model_validate({
            "schema_version": "1.0",
            "device_id": self.device_id,
            "session_id": self.session_id,
            "timestamp_ms": self.timestamp_ms,
            "data_origin": self.data_origin,
            "hr_bpm": self.hr_bpm,
            "gsr": {"raw": self.gsr_raw, "delta": self.gsr_delta},
            "movement": {"score": self.movement_score},
            "signal_quality": {
                "ppg": self.sq_ppg,
                "gsr": self.sq_gsr,
                "imu": self.sq_imu,
            },
            "prediction": {
                "probability": self.pred_prob,
                "state": self._derive_prediction_state(),
            },
            "firmware_version": self.firmware_version,
            "model_version": self.model_version,
        })


class MqttSubscriber:
    """Manages an async MQTT subscription integrated with FastAPI lifecycle."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._aggregators: dict[str, DeviceTelemetryAggregator] = {}

    def get_aggregator(self, device_id: str) -> DeviceTelemetryAggregator:
        if device_id not in self._aggregators:
            self._aggregators[device_id] = DeviceTelemetryAggregator(device_id)
        return self._aggregators[device_id]

    # -- public lifecycle ---------------------------------------------------

    async def start(self) -> None:
        """Spawn the subscriber background task. Safe to call multiple times."""
        if self._task is not None and not self._task.done():
            logger.warning("MQTT subscriber already running — skipping start")
            return
        self._task = asyncio.create_task(self._run_loop(), name="mqtt-subscriber")
        logger.info("MQTT subscriber task created")

    async def stop(self) -> None:
        """Cancel the background task and wait for clean exit."""
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("MQTT subscriber stopped")

    # -- internal -----------------------------------------------------------

    async def _run_loop(self) -> None:
        """Reconnect loop with exponential backoff."""
        settings = get_settings()
        delay = _RECONNECT_MIN_S

        while True:
            try:
                logger.info(
                    "Connecting to MQTT broker %s:%d …",
                    settings.mqtt_broker_host,
                    settings.mqtt_broker_port,
                )
                async with aiomqtt.Client(
                    hostname=settings.mqtt_broker_host,
                    port=settings.mqtt_broker_port,
                    username=settings.mqtt_username,
                    password=settings.mqtt_password,
                    identifier=f"asd-backend-{id(self):x}",
                ) as client:
                    logger.info("MQTT connected — subscribing to %s", TOPIC_FILTER)
                    await client.subscribe(TOPIC_FILTER, qos=QOS)
                    delay = _RECONNECT_MIN_S  # reset backoff on success

                    async for message in client.messages:
                        await self._handle_message(message)

            except aiomqtt.MqttError as exc:
                logger.warning("MQTT connection lost (%s) — retrying in %ds", exc, delay)
            except asyncio.CancelledError:
                logger.info("MQTT subscriber cancelled")
                raise
            except Exception:
                logger.exception("Unexpected error in MQTT loop — retrying in %ds", delay)

            await asyncio.sleep(delay)
            delay = min(delay * 2, _RECONNECT_MAX_S)

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        """Validate topic + payload, persist and broadcast."""
        topic_str = str(message.topic)

        # 1. Parse JSON payload
        try:
            raw: Any = json.loads(message.payload)
        except (json.JSONDecodeError, TypeError):
            logger.warning("MQTT payload is not valid JSON on %s — dropped", topic_str)
            return

        if not isinstance(raw, dict):
            logger.warning("MQTT payload is not a JSON object on %s — dropped", topic_str)
            return

        # 2. Check topic pattern: Unified Telemetry
        unified_match = UNIFIED_TOPIC_REGEX.match(topic_str)
        if unified_match is not None:
            topic_device_id = unified_match.group(1)
            try:
                telemetry = Telemetry.model_validate(raw)
            except Exception as exc:
                logger.warning("MQTT payload failed schema validation on %s: %s", topic_str, exc)
                return

            if telemetry.device_id != topic_device_id:
                logger.warning(
                    "device_id mismatch: topic=%s payload=%s — dropped",
                    topic_device_id,
                    telemetry.device_id,
                )
                return

            # Keep aggregator in sync
            aggregator = self.get_aggregator(topic_device_id)
            aggregator.update_unified(telemetry)

            await self._persist_and_broadcast(telemetry, topic_device_id)
            return

        # 3. Check topic pattern: Individual Sensor (ppg, gsr, imu)
        sensor_match = SENSOR_TOPIC_REGEX.match(topic_str)
        if sensor_match is not None:
            topic_device_id = sensor_match.group(1)
            sensor_type = sensor_match.group(2).lower()

            payload_device_id = raw.get("device_id")
            if payload_device_id is not None and payload_device_id != topic_device_id:
                logger.warning(
                    "device_id mismatch: topic=%s payload=%s — dropped",
                    topic_device_id,
                    payload_device_id,
                )
                return

            aggregator = self.get_aggregator(topic_device_id)
            if sensor_type == "ppg":
                aggregator.update_ppg(raw)
            elif sensor_type == "gsr":
                aggregator.update_gsr(raw)
            elif sensor_type == "imu":
                aggregator.update_imu(raw)
            else:
                logger.warning("Unknown sensor type '%s' on %s — dropped", sensor_type, topic_str)
                return

            try:
                telemetry = aggregator.to_telemetry()
            except Exception as exc:
                logger.warning("Aggregated telemetry failed validation for %s: %s", topic_device_id, exc)
                return

            await self._persist_and_broadcast(telemetry, topic_device_id)
            return

        logger.warning("Ignored message on unexpected topic: %s", topic_str)

    async def _persist_and_broadcast(self, telemetry: Telemetry, device_id: str) -> None:
        """Persist telemetry to DB and broadcast to WebSocket clients."""
        try:
            db = SessionLocal()
            try:
                persist_telemetry(db, telemetry)
            finally:
                db.close()
        except Exception:
            logger.exception("Failed to persist MQTT telemetry for %s", device_id)
            # Allow broadcast even if DB persist fails

        try:
            await manager.broadcast(telemetry.model_dump(mode="json"))
        except Exception:
            logger.exception("Failed to broadcast MQTT telemetry via WebSocket for %s", device_id)


# Module-level singleton
mqtt_subscriber = MqttSubscriber()

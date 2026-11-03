"""Không nhận topic tách sensor cũ hoặc body khác identity đã đăng ký."""
import asyncio
import json
import pytest
from fastapi import HTTPException
from app.main import app
from test_telemetry import payload


@pytest.mark.parametrize("topic", [
    "asd/v1/devices/SIM-001/telemetry", "asd/v1/devices/SIM-001/sensors/ppg",
    "asd/v1/devices/SIM-001/sensors/gsr", "asd/v1/devices/SIM-001/sensors/imu",
    "asd-ease/v1/DEVICE/SIM-001/telemetry",
])
def test_unregistered_topics_cannot_reach_ingestion(client, topic):
    with pytest.raises(HTTPException) as error:
        asyncio.run(app.state.mqtt.process(topic, json.dumps(payload()).encode(), False))
    assert error.value.status_code == 403

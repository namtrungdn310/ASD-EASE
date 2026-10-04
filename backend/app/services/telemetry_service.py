from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import Device, Event
from app.schemas.telemetry import Telemetry


def persist_telemetry(db: Session, telemetry: Telemetry) -> None:
    device = db.get(Device, telemetry.device_id)
    if device is None:
        device = Device(
            device_id=telemetry.device_id,
            firmware_version=telemetry.firmware_version,
            data_origin=telemetry.data_origin.value,
        )
        db.add(device)
    device.last_seen_at = datetime.now(timezone.utc)
    device.firmware_version = telemetry.firmware_version
    device.data_origin = telemetry.data_origin.value
    if telemetry.prediction.state.value in {"ATTENTION", "UNCERTAIN"}:
        db.add(Event(
            device_id=telemetry.device_id,
            session_id=telemetry.session_id,
            state=telemetry.prediction.state.value,
            probability=telemetry.prediction.probability,
            timestamp_ms=telemetry.timestamp_ms,
        ))
    db.commit()


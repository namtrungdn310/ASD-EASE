from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import Device, Event
from app.schemas.telemetry import Telemetry
from fastapi import HTTPException
import hashlib
import json
from app.db.models import Session as RecordingSession, TelemetryCursor
from app.services.transactions import write_transaction


async def receive_telemetry(db, payload, identity, runtime):
    from app.services.websocket_manager import manager
    from app.services.session_service import ensure_device
    live = runtime.is_live(identity.device_id)
    if not live:
        raise HTTPException(409, "CONNECTION_NOT_SYNCHRONIZED")
    if (payload.device_id, payload.data_origin) != (identity.device_id, identity.data_origin):
        raise HTTPException(403, "IDENTITY_MISMATCH")
    wire = payload.model_dump(mode="json")
    # Chuẩn hoá các trường đo số về float; không dùng hàm này cho JCS/raw.
    measured = payload.telemetry().model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(measured, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    scope = f"{identity.device_id}:{'session' if payload.session_id else 'boot'}:{payload.session_id or live.boot_id}"
    with write_transaction(db):
        device = ensure_device(db, identity)
        if (device.boot_id, device.connection_id) != (live.boot_id, live.connection_id):
            raise HTTPException(409, "BOOT_MISMATCH")
        if payload.session_id:
            row = db.get(RecordingSession, payload.session_id)
            if not row:
                raise HTTPException(404, "SESSION_NOT_FOUND")
            if (row.device_id, row.data_origin, row.boot_id) != (identity.device_id, identity.data_origin, live.boot_id):
                raise HTTPException(403, "IDENTITY_MISMATCH")
            if row.state not in {"RECORDING", "STOPPING"} or row.started_at is None:
                raise HTTPException(409, "SESSION_NOT_ACCEPTING")
            if row.cutoff_timestamp_ms is not None and payload.timestamp_ms >= row.cutoff_timestamp_ms:
                raise HTTPException(409, "SESSION_NOT_ACCEPTING")
        elif device.actual_state == "RECORDING":
            raise HTTPException(409, "SESSION_REQUIRED_WHILE_RECORDING")
        cursor = db.get(TelemetryCursor, scope)
        if cursor and payload.timestamp_ms <= cursor.timestamp_ms:
            if payload.timestamp_ms == cursor.timestamp_ms and cursor.digest == digest:
                return {"accepted": True, "duplicate": True}
            raise HTTPException(409, "TELEMETRY_CONFLICT_OR_STALE")
        if cursor:
            cursor.timestamp_ms, cursor.digest = payload.timestamp_ms, digest
        else:
            db.add(TelemetryCursor(identity=scope, timestamp_ms=payload.timestamp_ms, digest=digest))
        telemetry = payload.telemetry()
        persist_telemetry(db, telemetry, commit=False)
    await manager.broadcast(wire)
    return {"accepted": True, "duplicate": False}


def persist_telemetry(db: Session, telemetry: Telemetry, commit=True) -> None:
    device = db.get(Device, telemetry.device_id)
    if device is None:
        device = Device(
            device_id=telemetry.device_id,
            firmware_version=telemetry.firmware_version,
            data_origin=telemetry.data_origin.value,
        )
        db.add(device)
    device.last_seen_at = datetime.now(timezone.utc)
    device.last_telemetry_at = device.last_seen_at
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
    if commit:
        db.commit()


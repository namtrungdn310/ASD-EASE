"""Ý định và lệnh chờ cùng một transaction; ACK mới quyết định actual state."""
from datetime import datetime, timezone
import json
import time
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from app.db.models import Device, DeviceCommand, Session
from app.services.transactions import write_transaction


def now_ms():
    return int(time.time() * 1000)


def utc_now():
    return datetime.now(timezone.utc)


def ensure_device(db, identity):
    device = db.get(Device, identity.device_id)
    if device is None:
        device = Device(device_id=identity.device_id, data_origin=identity.data_origin,
                        firmware_version="unknown", generation=0, actual_state="UNKNOWN", unresolved=False)
        db.add(device)
        db.flush()
    elif device.data_origin != identity.data_origin:
        raise HTTPException(403, "IDENTITY_MISMATCH")
    return device


def serialize(row):
    fields = ("session_id", "device_id", "participant_id", "data_origin", "state", "desired_state",
              "actual_state", "command_id", "generation", "boot_id", "requested_at", "started_at",
              "stopped_at", "cutoff_timestamp_ms", "final_batch_id", "recording_complete", "empty_recording")
    result = {field: getattr(row, field) for field in fields}
    for field in ("requested_at", "started_at", "stopped_at"):
        if result[field] is not None and result[field].tzinfo is None:
            result[field] = result[field].replace(tzinfo=timezone.utc)
    result["incomplete_reasons"] = json.loads(row.incomplete_reasons_json)
    result["acquisition_profile"] = json.loads(row.acquisition_profile_json) if row.acquisition_profile_json else None
    return result


def enqueue_command(db, device, session, action, settings):
    if device.generation >= 2**53 - 1:
        raise HTTPException(409, "GENERATION_EXHAUSTED")
    device.generation += 1
    command = DeviceCommand(command_id=uuid4().hex, device_id=device.device_id,
                            session_id=session.session_id, generation=device.generation,
                            action=action, boot_id=device.boot_id,
                            expires_at_ms=now_ms() + settings.command_timeout_seconds * 1000, status="PENDING")
    db.add(command)
    session.command_id, session.generation = command.command_id, command.generation
    return command


def start_session(db, request, identity, settings):
    with write_transaction(db):
        old = db.get(Session, request.session_id)
        if old:
            if (old.device_id, old.participant_id, old.data_origin) != (request.device_id, request.participant_id, identity.data_origin):
                raise HTTPException(409, "SESSION_ID_CONFLICT")
            result = serialize(old)
            return result, 202 if old.state == "STARTING" else 200
        device = ensure_device(db, identity)
        if device.unresolved or db.scalar(select(Session.session_id).where(Session.device_id == request.device_id, Session.active.is_(True))):
            raise HTTPException(409, "DEVICE_BUSY_OR_UNRESOLVED")
        # Phiên legacy đang mở cần người vận hành đối chiếu, không suy là đã dừng.
        if db.scalar(select(Session.session_id).where(Session.device_id == request.device_id, Session.state == "LEGACY", Session.stopped_at.is_(None))) and (device.boot_id is None or device.actual_state not in {"IDLE", "STOPPED"}):
            raise HTTPException(409, "LEGACY_SESSION_UNRESOLVED")
        row = Session(**request.model_dump(), requested_at=utc_now(), data_origin=identity.data_origin,
                      state="STARTING", desired_state="RECORDING", actual_state=device.actual_state,
                      active=True, boot_id=device.boot_id, recording_complete=False, empty_recording=False,
                      incomplete_reasons_json='["RECORDING_NOT_FINISHED"]',
                      acquisition_profile_json=identity.acquisition_profile.model_dump_json())
        db.add(row)
        enqueue_command(db, device, row, "START", settings)
        db.flush()
        result = serialize(row)
    return result, 202


def stop_session(db, session_id, registry, settings):
    with write_transaction(db):
        row = db.get(Session, session_id)
        if row is None:
            raise HTTPException(404, "SESSION_NOT_FOUND")
        identity = registry.identity(row.device_id, row.data_origin)
        if row.state == "LEGACY":
            raise HTTPException(409, "LEGACY_SESSION_UNRESOLVED")
        if row.state in {"STOPPED", "ABORTED"}:
            return serialize(row), 200
        if row.state == "STOPPING":
            return serialize(row), 202
        previous = db.get(DeviceCommand, row.command_id)
        if previous and previous.status == "PENDING":
            previous.status = "SUPERSEDED"
        row.state, row.desired_state = "STOPPING", "STOPPED"
        device = ensure_device(db, identity)
        enqueue_command(db, device, row, "STOP", settings)
        db.flush()
        result = serialize(row)
    return result, 202


def abort_session(db, row, reason):
    row.state, row.active, row.actual_state = "ABORTED", False, "UNKNOWN"
    row.incomplete_reasons_json = json.dumps([reason])
    device = db.get(Device, row.device_id)
    device.unresolved, device.actual_state = True, "UNKNOWN"
    command = db.get(DeviceCommand, row.command_id)
    if command and command.status == "PENDING":
        command.status = "EXPIRED"


def expire_sessions(db):
    with write_transaction(db):
        for command in db.scalars(select(DeviceCommand).where(DeviceCommand.status == "PENDING", DeviceCommand.expires_at_ms <= now_ms())):
            row = db.get(Session, command.session_id)
            if row.command_id == command.command_id and row.active:
                abort_session(db, row, "COMMAND_TIMEOUT")
            command.status = "EXPIRED"
        for row in db.scalars(select(Session).where(Session.state == "STOPPING", Session.drain_deadline_ms <= now_ms())):
            row.state, row.active = "STOPPED", False
            row.incomplete_reasons_json = '["DRAIN_TIMEOUT","RAW_RECONCILIATION_PENDING_BRANCH06"]'


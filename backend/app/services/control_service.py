"""Đối chiếu boot/connection/lease và lưu ACK trước khi xác nhận cho thiết bị."""
import json
from fastapi import HTTPException
from sqlalchemy import select
from app.db.models import CommandLease, Device, DeviceCommand, DeviceConnection, Session, SyncNonce
from app.schemas.control import Command, StateResponse
from app.services.session_service import abort_session, ensure_device, now_ms, utc_now
from app.services.transactions import write_transaction


def business_ack(ack):
    data = ack.model_dump(mode="json")
    for name in ("connection_id", "request_id"):
        data.pop(name)
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _apply_ack(db, identity, ack):
    device = ensure_device(db, identity)
    if (device.boot_id, device.connection_id) != (ack.boot_id, ack.connection_id):
        raise HTTPException(409, "CONNECTION_MISMATCH")
    nonce = db.get(SyncNonce, f"{identity.device_id}:{ack.boot_id}:{ack.connection_id}:{ack.request_id}")
    if nonce is None or device.sync_request_id != ack.request_id or nonce.received_at_ms + 30000 <= now_ms():
        raise HTTPException(409, "LEASE_EXPIRED")
    command = db.get(DeviceCommand, ack.command_id)
    if not command or (command.device_id, command.session_id, command.generation, command.action, command.boot_id) != (
        ack.device_id, ack.session_id, ack.generation, ack.action, ack.boot_id
    ):
        raise HTTPException(409, "COMMAND_CONFLICT")
    value = business_ack(ack)
    if command.ack_json:
        if command.ack_json != value:
            raise HTTPException(409, "ACK_CONFLICT")
        return
    lease = db.get(CommandLease, f"{command.command_id}:{ack.connection_id}:{ack.request_id}")
    if not lease:
        # Sau reconnect, thiết bị bọc lại ACK đã thực thi bằng nonce hiện hành.
        lease = db.scalar(select(CommandLease).where(CommandLease.command_id == command.command_id, CommandLease.boot_id == ack.boot_id))
    if not lease or lease.boot_id != ack.boot_id or lease.expires_at_ms <= now_ms():
        raise HTTPException(409, "LEASE_EXPIRED")
    row = db.get(Session, command.session_id)
    # ACK lệnh đã bị Stop thay thế chỉ lưu tra soát, không đổi vòng đời.
    if command.status == "SUPERSEDED":
        command.ack_json = value
        if ack.result == "STARTED" and row.started_at is None:
            row.started_at = utc_now()
        return
    if command.status != "PENDING" or command.expires_at_ms <= now_ms() or row.command_id != command.command_id:
        raise HTTPException(409, "STALE_COMMAND")
    if ack.result == "STOPPED":
        summary = ack.final_summary
        profile = json.loads(row.acquisition_profile_json)
        if summary.raw_recording_enabled:
            for stream in ("ppg", "imu", "gsr"):
                slots = summary.cutoff_timestamp_ms * profile[f"{stream}_hz"]
                if slots % 1000 or slots // 1000 != getattr(summary.slot_counts, stream):
                    raise HTTPException(422, "SUMMARY_TIMELINE_MISMATCH")
            if summary.total_generated_batches != (summary.cutoff_timestamp_ms + 999) // 1000:
                raise HTTPException(422, "SUMMARY_BATCH_COUNT_MISMATCH")
        elif summary.total_generated_batches:
            raise HTTPException(422, "RAW_DISABLED_WITH_BATCHES")
    command.ack_json, command.status = value, "ACKED"
    if ack.result == "REJECTED":
        abort_session(db, row, ack.reason)
        return
    device.actual_state = row.actual_state = "RECORDING" if ack.result == "STARTED" else "STOPPED"
    if ack.result == "STARTED":
        if row.state != "STARTING":
            raise HTTPException(409, "SESSION_NOT_ACCEPTING")
        row.state, row.started_at = "RECORDING", utc_now()
    else:
        row.stopped_at, row.cutoff_timestamp_ms = utc_now(), ack.timestamp_ms
        row.final_summary_json, row.final_batch_id = summary.model_dump_json(), summary.final_batch_id
        row.empty_recording = summary.total_generated_batches == 0
        if not summary.raw_recording_enabled:
            row.state, row.active = "STOPPED", False
            row.incomplete_reasons_json = '["RAW_RECORDING_DISABLED"]'
        elif row.empty_recording:
            row.state, row.active, row.recording_complete = "STOPPED", False, True
            row.incomplete_reasons_json = "[]"
        else:
            from app.core.config import get_settings
            row.drain_deadline_ms = now_ms() + get_settings().drain_timeout_seconds * 1000
            row.incomplete_reasons_json = '["RAW_RECONCILIATION_PENDING_BRANCH06"]'


def apply_ack(db, identity, ack):
    with write_transaction(db):
        _apply_ack(db, identity, ack)


def synchronize(db, identity, request):
    with write_transaction(db):
        device = ensure_device(db, identity)
        if request.last_generation > device.generation:
            raise HTTPException(409, "STALE_COMMAND")
        nonce_key = f"{identity.device_id}:{request.boot_id}:{request.connection_id}:{request.request_id}"
        nonce = db.get(SyncNonce, nonce_key)
        if nonce is None:
            nonce = SyncNonce(identity=nonce_key, device_id=identity.device_id, connection_id=request.connection_id,
                              request_id=request.request_id, received_at_ms=now_ms())
            db.add(nonce)
        elif nonce.received_at_ms + 30000 <= now_ms():
            raise HTTPException(409, "LEASE_EXPIRED")
        elif device.sync_request_id != request.request_id:
            raise HTTPException(409, "STALE_COMMAND")
        device.sync_request_id = request.request_id
        key = f"{identity.device_id}:{request.boot_id}:{request.connection_id}"
        previous = db.get(DeviceConnection, key)
        if previous and (device.boot_id, device.connection_id) != (request.boot_id, request.connection_id):
            raise HTTPException(409, "CONNECTION_MISMATCH")
        if device.boot_id != request.boot_id:
            old_boot = db.scalar(select(DeviceConnection.identity).where(DeviceConnection.device_id == identity.device_id, DeviceConnection.boot_id == request.boot_id))
            if old_boot:
                raise HTTPException(409, "BOOT_MISMATCH")
            if device.boot_id is not None:
                for row in db.scalars(select(Session).where(Session.device_id == device.device_id, Session.active.is_(True))):
                    abort_session(db, row, "INTERRUPTED_REBOOT")
                device.unresolved = request.actual_state not in {"IDLE", "STOPPED"}
            device.boot_id = request.boot_id
        device.connection_id = request.connection_id
        if not previous:
            db.add(DeviceConnection(identity=key, device_id=device.device_id, boot_id=request.boot_id, connection_id=request.connection_id))
        for command in db.scalars(select(DeviceCommand).where(DeviceCommand.device_id == device.device_id, DeviceCommand.status == "PENDING", DeviceCommand.boot_id.is_(None))):
            command.boot_id = request.boot_id
            db.get(Session, command.session_id).boot_id = request.boot_id
        error = None
        if request.last_ack:
            ack = request.last_ack
            if (ack.device_id, ack.data_origin, ack.boot_id, ack.connection_id) != (request.device_id, request.data_origin, request.boot_id, request.connection_id):
                error = "IDENTITY_MISMATCH"
            else:
                # Savepoint: ACK không hợp lệ không làm mất đồng bộ kết nối hợp lệ.
                try:
                    with db.begin_nested():
                        _apply_ack(db, identity, ack)
                except HTTPException as exception:
                    error = exception.detail
        db.flush()
        row = db.scalar(select(Session).where(Session.device_id == device.device_id).order_by(Session.requested_at.desc()))
        active = db.scalar(select(Session).where(Session.device_id == device.device_id, Session.active.is_(True)))
        if not active:
            if request.actual_state in {"IDLE", "STOPPED"}:
                device.unresolved = False
                device.actual_state = request.actual_state
            else:
                device.unresolved, device.actual_state = True, "UNKNOWN"
                error = error or "SESSION_NOT_ACCEPTING"
        elif active.state in {"RECORDING", "STOPPING"} and request.actual_state == "RECORDING":
            if request.session_id != active.session_id or active.boot_id != request.boot_id:
                abort_session(db, active, "SESSION_NOT_ACCEPTING")
                error = "SESSION_NOT_ACCEPTING"
        elif active.state == "RECORDING" and request.actual_state != "RECORDING":
            abort_session(db, active, "SESSION_NOT_ACCEPTING")
            error = "SESSION_NOT_ACCEPTING"
        elif active.state == "STARTING" and request.actual_state == "RECORDING" and not request.last_ack:
            # Không thay ACK bằng lời khai trạng thái hoặc PUBACK.
            error = "SESSION_NOT_ACCEPTING"
        db.flush()
        accepted = None
        if request.last_command_id:
            command = db.get(DeviceCommand, request.last_command_id)
            if command and command.device_id == device.device_id and command.boot_id == request.boot_id and command.generation == request.last_generation and command.ack_json and command.status == "ACKED":
                accepted = command.command_id
        return StateResponse(control_version="1.0", message_type="STATE_RESPONSE", device_id=device.device_id,
                             data_origin=identity.data_origin, boot_id=request.boot_id, connection_id=request.connection_id,
                             request_id=request.request_id, session_id=row.session_id if row else None,
                             state=row.state if row and row.state != "LEGACY" else "IDLE", generation=device.generation,
                             accepted_command_id=accepted, pending_command=None, error_code=error)


def lease_command(db, identity, boot_id, connection_id, request_id):
    with write_transaction(db):
        device = ensure_device(db, identity)
        if (device.boot_id, device.connection_id) != (boot_id, connection_id):
            return None
        command = db.scalar(select(DeviceCommand).where(DeviceCommand.device_id == identity.device_id, DeviceCommand.status == "PENDING"))
        if not command or command.boot_id != boot_id or command.expires_at_ms <= now_ms():
            return None
        key = f"{command.command_id}:{connection_id}:{request_id}"
        lease = db.get(CommandLease, key)
        if not lease:
            lease = CommandLease(lease_id=key, command_id=command.command_id, boot_id=boot_id, connection_id=connection_id,
                                 request_id=request_id, expires_at_ms=command.expires_at_ms)
            db.add(lease)
        remaining = lease.expires_at_ms - now_ms()
        if remaining <= 0:
            return None
        row = db.get(Session, command.session_id)
        return Command(control_version="1.0", message_type="COMMAND", device_id=identity.device_id,
                       data_origin=identity.data_origin, boot_id=boot_id, connection_id=connection_id,
                       request_id=request_id, command_id=command.command_id, generation=command.generation,
                       session_id=command.session_id, action=command.action, expires_in_ms=min(30000, remaining),
                       acquisition_profile=json.loads(row.acquisition_profile_json) if command.action == "START" else None)

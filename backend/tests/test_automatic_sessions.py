"""Tự tạo một phiên mỗi boot DEVICE, không phụ thuộc trang web hay nhãn online."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from unittest.mock import Mock

from sqlalchemy import select
from app.main import app
from app.db.database import SessionLocal
from app.db.models import Device, DeviceCommand, Session
from app.schemas.control import StateRequest
from app.services.session_service import ensure_automatic_session
from conftest import OP_HEADERS, sync_payload


def setup(runtime, monkeypatch):
    monkeypatch.setattr(runtime.settings, "auto_session_enabled", True)
    monkeypatch.setattr(runtime.settings, "auto_session_device_id", "ESP-001")
    identity = runtime.registry.identity("ESP-001", "DEVICE")
    runtime.sync(identity, StateRequest.model_validate(sync_payload(device_id="ESP-001", data_origin="DEVICE")))
    return identity


def create(runtime, identity, boot="BOOT-UNIT"):
    with SessionLocal() as db:
        return ensure_automatic_session(db, identity, boot, runtime.settings)


def rows():
    with SessionLocal() as db:
        return list(db.scalars(select(Session).where(Session.device_id == "ESP-001")))


def test_disabled_by_default_and_does_not_create_before_sync(client, monkeypatch):
    runtime = app.state.mqtt
    identity = runtime.registry.identity("ESP-001", "DEVICE")
    assert not create(runtime, identity)
    monkeypatch.setattr(runtime.settings, "auto_session_enabled", True)
    monkeypatch.setattr(runtime.settings, "auto_session_device_id", "ESP-001")
    assert not create(runtime, identity)
    assert rows() == []


def test_creates_one_pending_start_per_boot_not_recording_before_ack(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    assert create(runtime, identity)
    assert not create(runtime, identity)
    record, = rows()
    assert record.state == "STARTING" and record.started_at is None
    assert record.session_id.startswith("AUTO-") and record.boot_id == "BOOT-UNIT"
    assert not record.recording_complete
    with SessionLocal() as db:
        command = db.get(DeviceCommand, record.command_id)
        assert command.action == "START" and command.status == "PENDING"


def test_dispatch_ack_and_live_telemetry_follow_existing_protocol(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    runtime.connected = True
    runtime.client = Mock()
    runtime.client.publish.return_value.rc = 0
    asyncio.run(runtime.dispatch())
    record, = rows()
    packet = json.loads(runtime.client.publish.call_args.args[1])
    assert packet["message_type"] == "COMMAND" and packet["action"] == "START"
    assert packet["session_id"] == record.session_id
    ack = {key: packet[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id",
        "request_id", "command_id", "generation", "session_id", "action")}
    ack.update(message_type="ACK", result="STARTED", timestamp_ms=0, reason=None, final_summary=None)
    asyncio.run(runtime.process(runtime.prefix(identity)+"ack", json.dumps(ack).encode(), False))
    record, = rows()
    assert record.state == "RECORDING" and record.started_at is not None
    asyncio.run(runtime.dispatch())
    assert len(rows()) == 1


def test_reload_page_and_resync_do_not_create_another_session(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    assert create(runtime, identity)
    first = rows()[0].session_id
    for _ in range(3):
        assert client.get("/api/v1/sessions", headers=OP_HEADERS).status_code == 200
        runtime.sync(identity, StateRequest.model_validate(sync_payload(device_id="ESP-001", data_origin="DEVICE")))
        assert not create(runtime, identity)
    assert [row.session_id for row in rows()] == [first]


def test_expired_start_does_not_restart_forever(client, monkeypatch):
    from app.services.session_service import expire_sessions
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    assert create(runtime, identity)
    record, = rows()
    with SessionLocal() as db:
        db.get(DeviceCommand, record.command_id).expires_at_ms = 0
        db.commit()
        expire_sessions(db)
    record, = rows()
    assert record.state == "ABORTED"
    runtime.sync(identity, StateRequest.model_validate(sync_payload(device_id="ESP-001", data_origin="DEVICE")))
    assert not create(runtime, identity)
    assert len(rows()) == 1


def test_reconnect_same_boot_and_new_runtime_reuse_durable_session(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    assert create(runtime, identity)
    first = rows()[0].session_id
    runtime.live.clear()
    runtime.sync(identity, StateRequest.model_validate(sync_payload(connection="CONN-NEW", device_id="ESP-001", data_origin="DEVICE")))
    from app.services.mqtt_runtime import MQTTRuntime
    restarted = MQTTRuntime(runtime.settings, runtime.registry, SessionLocal)
    assert not create(restarted, identity)
    assert [row.session_id for row in rows()] == [first]


def test_new_boot_interrupts_old_session_and_creates_new_epoch_session(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    assert create(runtime, identity)
    previous = rows()[0].session_id
    runtime.sync(identity, StateRequest.model_validate(sync_payload(boot="BOOT-NEW", connection="CONN-NEW", request="REQ-NEW",
        device_id="ESP-001", data_origin="DEVICE")))
    assert create(runtime, identity, "BOOT-NEW")
    records = rows()
    assert len(records) == 2
    old = next(row for row in records if row.session_id == previous)
    assert old.state == "ABORTED"
    assert any(row.boot_id == "BOOT-NEW" and row.state == "STARTING" for row in records)


def test_manual_stop_or_failure_does_not_trigger_endless_auto_start(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    assert create(runtime, identity)
    with SessionLocal() as db:
        record = db.get(Session, rows()[0].session_id)
        record.active = False
        record.state = "STOPPED"
        db.get(Device, "ESP-001").actual_state = "STOPPED"
        db.commit()
    assert not create(runtime, identity)
    assert len(rows()) == 1


def test_other_identity_source_boot_or_unresolved_device_cannot_auto_start(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    assert not create(runtime, identity, "OLD-BOOT")
    assert not create(runtime, runtime.registry.identity("SIM-001"))
    monkeypatch.setattr(runtime.settings, "auto_session_device_id", "ESP-OTHER")
    assert not create(runtime, identity)
    monkeypatch.setattr(runtime.settings, "auto_session_device_id", "ESP-001")
    with SessionLocal() as db:
        db.get(Device, "ESP-001").unresolved = True
        db.commit()
    assert not create(runtime, identity)
    assert rows() == []


def test_concurrent_checks_create_only_one_start_command(client, monkeypatch):
    runtime = app.state.mqtt
    identity = setup(runtime, monkeypatch)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: create(runtime, identity), range(2)))
    assert sorted(results) == [False, True]
    assert len(rows()) == 1

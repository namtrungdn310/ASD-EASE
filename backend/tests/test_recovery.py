import asyncio
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi import HTTPException
import pytest
from sqlalchemy import select
from app.db.database import SessionLocal
from app.db.models import DeviceCommand, Session
from app.schemas.control import StateRequest
from app.services.mqtt_runtime import MQTTRuntime, ReceiverLock
from app.services.session_service import expire_sessions
from conftest import OP_HEADERS, start_recording, sync_payload
from test_lifecycle import get_session, stop_ack
from test_telemetry import payload


def test_persisted_unsent_start_survives_new_runtime(client):
    from app.main import app
    result = client.post("/api/v1/sessions/start", headers=OP_HEADERS, json={"device_id": "SIM-001", "session_id": "PENDING"}).json()
    new = MQTTRuntime(app.state.settings, app.state.registry, SessionLocal)
    response = new.sync(app.state.registry.by_id["SIM-001"], StateRequest.model_validate(sync_payload(request="AFTER-CRASH")))
    assert response.pending_command.command_id == result["command_id"]
    assert response.pending_command.generation == result["generation"]
    assert get_session(client)["state"] == "STARTING"


def test_sync_last_ack_after_reconnect_confirms_without_new_epoch(client, recording):
    ack = recording | {"connection_id": "RECONNECTED", "request_id": "REQ-RECONNECTED"}
    request = sync_payload(connection="RECONNECTED", request="REQ-RECONNECTED", actual_state="RECORDING", session_id=recording["session_id"],
        last_command_id=ack["command_id"], last_generation=ack["generation"], last_ack=ack)
    result = client.post("/api/v1/devices/sync", json=request)
    assert result.status_code == 200, result.text
    assert result.json()["accepted_command_id"] == ack["command_id"]
    assert result.json()["state"] == "RECORDING" and result.json()["pending_command"] is None
    assert client.post("/api/v1/devices/ack", json=recording).status_code == 409


def test_not_yet_persisted_ack_can_be_wrapped_after_reconnect(client):
    client.post("/api/v1/sessions/start", headers=OP_HEADERS, json={"device_id": "SIM-001", "session_id": "PENDING"})
    command = client.post("/api/v1/devices/sync", json=sync_payload(request="ISSUED")).json()["pending_command"]
    ack = {key: command[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id", "command_id", "generation", "session_id", "action")}
    ack.update(message_type="ACK", connection_id="NEW-CONNECTION", request_id="NEW-REQUEST", result="STARTED", timestamp_ms=0, reason=None, final_summary=None)
    request = sync_payload(connection="NEW-CONNECTION", request="NEW-REQUEST", actual_state="RECORDING", session_id="PENDING",
        last_command_id=ack["command_id"], last_generation=ack["generation"], last_ack=ack)
    result = client.post("/api/v1/devices/sync", json=request)
    assert result.status_code == 200, result.text
    assert result.json()["error_code"] is None
    assert result.json()["accepted_command_id"] == ack["command_id"]
    assert get_session(client)["state"] == "RECORDING"


def test_wrong_ack_and_missing_lease_do_not_start(client):
    client.post("/api/v1/sessions/start", headers=OP_HEADERS, json={"device_id": "SIM-001", "session_id": "PENDING"})
    command = client.post("/api/v1/devices/sync", json=sync_payload(request="ISSUED")).json()["pending_command"]
    ack = {key: command[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id", "command_id", "generation", "session_id", "action")}
    ack.update(message_type="ACK", result="STARTED", timestamp_ms=0, reason=None, final_summary=None)
    for changes in ({"command_id": "WRONG"}, {"generation": command["generation"] + 1}, {"boot_id": "OLD-BOOT"}, {"request_id": "UNKNOWN-NONCE"}):
        assert client.post("/api/v1/devices/ack", json=ack | changes).status_code == 409
    assert get_session(client)["state"] == "STARTING"
    with SessionLocal() as db:
        from app.db.models import CommandLease
        lease = db.scalar(select(CommandLease))
        lease.expires_at_ms = 0
        db.commit()
    assert client.post("/api/v1/devices/ack", json=ack).status_code == 409
    assert get_session(client)["state"] == "STARTING"


def test_stop_timeout_is_aborted_unknown(client, recording):
    client.post("/api/v1/sessions/stop", json={"session_id": recording["session_id"]}, headers=OP_HEADERS)
    with SessionLocal() as db:
        command = db.get(DeviceCommand, db.get(Session, recording["session_id"]).command_id)
        command.expires_at_ms = 0
        db.commit()
        expire_sessions(db)
    row = get_session(client)
    assert row["state"] == "ABORTED" and row["actual_state"] == "UNKNOWN"
    assert not row["recording_complete"]


def test_summary_conflict_cannot_overwrite_cutoff(client, recording):
    ack = stop_ack(client, raw=True, cutoff=1000, total=1)
    assert client.post("/api/v1/devices/ack", json=ack).status_code == 200
    changed = copy.deepcopy(ack)
    changed["final_summary"]["missing_samples"]["ppg"] = 1
    assert client.post("/api/v1/devices/ack", json=changed).status_code == 409
    assert get_session(client)["cutoff_timestamp_ms"] == 1000


def test_bad_summary_timing_is_rejected(client, recording):
    ack = stop_ack(client, raw=True, cutoff=1100, total=2)
    ack["final_summary"]["slot_counts"]["ppg"] += 1
    assert client.post("/api/v1/devices/ack", json=ack).status_code == 422
    assert get_session(client)["actual_state"] == "RECORDING"


def test_old_or_retained_presence_does_not_remove_live_connection(client):
    from app.main import app
    runtime = app.state.mqtt
    data = {key: value for key, value in sync_payload().items() if key in {"control_version", "device_id", "data_origin", "boot_id", "connection_id"}}
    data.update(message_type="PRESENCE", status="OFFLINE", connection_id="STALE")
    topic = "asd-ease/v1/SYNTHETIC/SIM-001/presence"
    # Chỉ kiểm tra phần presence, dùng identity MQTT riêng để bảo đảm nhánh xử lý được gọi.
    identity = app.state.registry.by_id["SIM-001"]
    identity.transport = "mqtt"
    try:
        asyncio.run(runtime.process(topic, json.dumps(data).encode(), True))
        assert runtime.is_live("SIM-001")
        asyncio.run(runtime.process(topic, json.dumps(data).encode(), False))
        assert runtime.is_live("SIM-001")
    finally:
        identity.transport = "http"


def test_single_receiver_lock_is_released(tmp_path):
    first, second = ReceiverLock(tmp_path / "receiver.lock"), ReceiverLock(tmp_path / "receiver.lock")
    first.acquire()
    try:
        with pytest.raises(RuntimeError):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_new_request_cannot_replay_old_sync_nonce(client):
    assert client.post("/api/v1/devices/sync", json=sync_payload(request="NEW-REQUEST")).status_code == 200
    assert client.post("/api/v1/devices/sync", json=sync_payload()).status_code == 409


def test_raw_before_start_ack_and_path_ids_rejected(client):
    from test_raw_batch import raw_payload
    client.post("/api/v1/sessions/start", headers=OP_HEADERS, json={"device_id": "SIM-001", "session_id": "SYN-SESSION001"})
    assert client.post("/api/v1/raw-batch", json=raw_payload()).status_code == 409
    assert client.post("/api/v1/raw-batch", json=raw_payload() | {"session_id": "../escape"}).status_code == 422


def test_started_recording_cannot_omit_session(client, recording):
    assert client.post("/api/v1/telemetry", json=payload()).status_code == 409


def test_broker_down_health_stays_available(client):
    assert client.get("/api/v1/health").status_code == 200
    result = client.get("/api/v1/health/mqtt", headers=OP_HEADERS)
    assert result.status_code == 200 and not result.json()["connected"]
    assert client.get("/api/v1/sessions", headers=OP_HEADERS).status_code == 200

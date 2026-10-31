import copy
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from app.core.security import Registry
from app.db.database import SessionLocal, engine
from app.db.models import Device, DeviceCommand, Session
from app.schemas.control import Ack, StateRequest
from app.schemas.session import SessionStart
from app.services.control_service import apply_ack
from app.services.session_service import expire_sessions, now_ms, start_session
from conftest import DEVICE_HEADERS, OP_HEADERS, start_recording, sync_payload


def stop_ack(client, *, raw=False, cutoff=0, total=0):
    result = client.post("/api/v1/sessions/stop", json={"session_id": "SYN-SESSION001"}, headers=OP_HEADERS)
    assert result.status_code == 202, result.text
    command = client.post("/api/v1/devices/sync", json=sync_payload(request="REQ-STOP", actual_state="RECORDING", session_id="SYN-SESSION001")).json()["pending_command"]
    ack = {key: command[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id", "command_id", "generation", "session_id", "action")}
    ack.update(message_type="ACK", result="STOPPED", timestamp_ms=cutoff, reason=None, final_summary={
        "cutoff_timestamp_ms": cutoff, "final_batch_id": total - 1 if total else None, "total_generated_batches": total,
        "dropped_batches": 0, "slot_counts": {"ppg": cutoff*50//1000, "imu": cutoff*50//1000, "gsr": cutoff*20//1000},
        "missing_samples": {"ppg": 0, "imu": 0, "gsr": 0}, "dropped_batch_ranges": [],
        "loss_ranges_truncated": False, "raw_recording_enabled": raw})
    return ack


def get_session(client):
    return client.get("/api/v1/sessions", headers=OP_HEADERS).json()[0]


def test_start_persists_command_before_ack_and_is_idempotent(client):
    body = {"device_id": "SIM-001", "session_id": "SYN-SESSION001"}
    first = client.post("/api/v1/sessions/start", json=body, headers=OP_HEADERS)
    second = client.post("/api/v1/sessions/start", json=body, headers=OP_HEADERS)
    assert first.status_code == second.status_code == 202
    assert first.json()["command_id"] == second.json()["command_id"]
    assert first.json()["state"] == "STARTING" and first.json()["started_at"] is None
    with SessionLocal() as db:
        assert db.get(DeviceCommand, first.json()["command_id"]).status == "PENDING"
    assert client.post("/api/v1/sessions/start", json=body | {"participant_id": "OTHER"}, headers=OP_HEADERS).status_code == 409
    assert client.post("/api/v1/sessions/start", json=body | {"session_id": "OTHER"}, headers=OP_HEADERS).status_code == 409


def test_started_ack_replay_and_conflict(client, recording):
    assert get_session(client)["state"] == "RECORDING"
    assert client.post("/api/v1/devices/ack", json=recording).status_code == 200
    changed = copy.deepcopy(recording)
    changed.update(result="REJECTED", reason="BUSY")
    result = client.post("/api/v1/devices/ack", json=changed)
    assert result.status_code == 409 and result.json()["detail"] == "ACK_CONFLICT"
    assert get_session(client)["state"] == "RECORDING"


def test_stop_zero_batch_does_not_claim_raw_recorded(client, recording):
    ack = stop_ack(client)
    result = client.post("/api/v1/devices/ack", json=ack)
    assert result.status_code == 200, result.text
    row = get_session(client)
    assert row["state"] == "STOPPED" and row["actual_state"] == "STOPPED"
    assert not row["recording_complete"] and row["empty_recording"]
    assert row["incomplete_reasons"] == ["RAW_RECORDING_DISABLED"]
    assert client.post("/api/v1/sessions/stop", json={"session_id": row["session_id"]}, headers=OP_HEADERS).status_code == 200


def test_stop_empty_raw_and_drain_timeout(client, recording):
    ack = stop_ack(client, raw=True, cutoff=1000, total=1)
    assert client.post("/api/v1/devices/ack", json=ack).status_code == 200
    assert get_session(client)["state"] == "STOPPING"
    with SessionLocal() as db:
        db.get(Session, "SYN-SESSION001").drain_deadline_ms = 0
        db.commit()
        expire_sessions(db)
    row = get_session(client)
    assert row["state"] == "STOPPED" and not row["recording_complete"]
    assert "DRAIN_TIMEOUT" in row["incomplete_reasons"]


def test_stop_supersedes_unacknowledged_start(client):
    client.post("/api/v1/sessions/start", json={"device_id": "SIM-001", "session_id": "SYN-SESSION001"}, headers=OP_HEADERS)
    first = client.post("/api/v1/devices/sync", json=sync_payload(request="REQ-FIRST")).json()["pending_command"]
    second = client.post("/api/v1/sessions/stop", json={"session_id": "SYN-SESSION001"}, headers=OP_HEADERS).json()
    late = {key: first[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id", "command_id", "generation", "session_id", "action")}
    late.update(message_type="ACK", result="STARTED", timestamp_ms=0, reason=None, final_summary=None)
    assert client.post("/api/v1/devices/ack", json=late).status_code == 200
    row = get_session(client)
    assert row["state"] == "STOPPING" and row["command_id"] == second["command_id"]
    assert row["started_at"] is not None


def test_timeout_blocks_start_until_idle_sync(client):
    client.post("/api/v1/sessions/start", json={"device_id": "SIM-001", "session_id": "SYN-SESSION001"}, headers=OP_HEADERS)
    with SessionLocal() as db:
        command = db.scalar(select(DeviceCommand))
        command.expires_at_ms = 0
        db.commit()
        expire_sessions(db)
    assert get_session(client)["state"] == "ABORTED"
    body = {"device_id": "SIM-001", "session_id": "NEW"}
    assert client.post("/api/v1/sessions/start", json=body, headers=OP_HEADERS).status_code == 409
    assert client.post("/api/v1/devices/sync", json=sync_payload(request="REQ-IDLE")).status_code == 200
    assert client.post("/api/v1/sessions/start", json=body, headers=OP_HEADERS).status_code == 202


def test_reboot_aborts_and_old_connection_cannot_return(client, recording):
    reboot = sync_payload(boot="BOOT-NEW", connection="CONN-NEW", request="REQ-NEW")
    assert client.post("/api/v1/devices/sync", json=reboot).status_code == 200
    assert get_session(client)["state"] == "ABORTED"
    assert client.post("/api/v1/devices/sync", json=sync_payload(request="REQ-OLD")).status_code == 409
    assert client.post("/api/v1/devices/ack", json=recording).status_code == 409


def test_concurrent_starts_have_one_winner(client):
    from app.main import app
    identity = app.state.registry.by_id["SIM-001"]
    def invoke(index):
        from fastapi import HTTPException
        with SessionLocal() as db:
            try:
                return start_session(db, SessionStart(session_id=f"CONCURRENT-{index}", device_id="SIM-001"), identity, app.state.settings)[1]
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(invoke, range(2))) == [202, 409]

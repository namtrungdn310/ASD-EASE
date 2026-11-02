"""Kiểm tra nhanh ví dụ đặc tả, chỉ đọc; không triển khai điều khiển thực tế.

Chạy từ thư mục gốc: .venv/Scripts/python.exe docs/contracts/check_examples.py
Chỉ nạp schema; không khởi động app, mở DB hoặc gửi mạng.
"""
import copy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import ValidationError
from app.schemas.raw_batch import RawBatch
from app.schemas.session import SessionStart, SessionStop
from app.schemas.telemetry import Telemetry

CATALOG = Path(__file__).with_name("examples.json")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
COMMON = {"control_version", "message_type", "device_id", "data_origin", "boot_id", "connection_id"}
FIELDS = {
    "STATE_REQUEST": {"request_id", "actual_state", "session_id", "last_command_id", "last_generation", "timestamp_ms", "last_ack"},
    "STATE_RESPONSE": {"request_id", "session_id", "state", "generation", "accepted_command_id", "pending_command", "error_code"},
    "COMMAND": {"request_id", "command_id", "generation", "session_id", "action", "expires_in_ms", "acquisition_profile"},
    "ACK": {"request_id", "command_id", "generation", "session_id", "action", "result", "timestamp_ms", "reason", "final_summary"},
    "PRESENCE": {"status"},
}
TOPICS = {"STATE_REQUEST": "state/request", "STATE_RESPONSE": "state/response", "COMMAND": "command", "ACK": "ack", "PRESENCE": "presence"}


def integer(value, minimum=0, maximum=2**53 - 1):
    assert type(value) is int and minimum <= value <= maximum, value


def counts(value):
    assert set(value) == {"ppg", "imu", "gsr"}
    for count in value.values():
        integer(count)


def control(payload):
    """Kiểm tra một phần cấu trúc mẫu; nhánh tính năng cần kiểm thử thực tế."""
    kind = payload["message_type"]
    assert set(payload) == COMMON | FIELDS[kind], kind
    assert payload["control_version"] == "1.0"
    assert payload["data_origin"] == "SYNTHETIC", "All catalog examples must be fixtures"
    assert len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) <= 4096
    for key, value in payload.items():
        if key.endswith("_id") and value is not None:
            assert isinstance(value, str) and ID.fullmatch(value), (key, value)
    if "generation" in payload:
        integer(payload["generation"], 1 if kind in {"COMMAND", "ACK"} else 0)
    if "timestamp_ms" in payload:
        integer(payload["timestamp_ms"])
    if kind == "STATE_REQUEST":
        integer(payload["last_generation"])
        assert payload["actual_state"] in {"IDLE", "RECORDING", "STOPPED"}
        if payload["last_ack"] is not None:
            assert payload["last_ack"]["message_type"] == "ACK"
            control(payload["last_ack"])
    if kind == "STATE_RESPONSE":
        assert payload["state"] in {"IDLE", "STARTING", "RECORDING", "STOPPING", "STOPPED", "ABORTED"}
        if payload["pending_command"] is not None:
            assert payload["pending_command"]["message_type"] == "COMMAND"
            control(payload["pending_command"])
    if kind == "COMMAND":
        integer(payload["expires_in_ms"], 1, 30000)
        assert payload["action"] in {"START", "STOP"}
        profile = payload["acquisition_profile"]
        if payload["action"] == "STOP":
            assert profile is None
        else:
            assert set(profile) == {"ppg_hz", "imu_hz", "gsr_hz", "window_ms"}
            assert profile["window_ms"] == 1000
            for name in ("ppg_hz", "imu_hz", "gsr_hz"):
                integer(profile[name], 1, 1000)
    if kind == "ACK":
        assert payload["action"] in {"START", "STOP"}
        result = payload["result"]
        assert result in {"STARTED", "STOPPED", "REJECTED"}
        if result == "REJECTED":
            assert isinstance(payload["reason"], str) and payload["final_summary"] is None
        elif result == "STARTED":
            assert payload["action"] == "START" and payload["timestamp_ms"] == 0
            assert payload["reason"] is None and payload["final_summary"] is None
        else:
            assert payload["action"] == "STOP" and payload["reason"] is None
            summary = payload["final_summary"]
            assert set(summary) == {"cutoff_timestamp_ms", "final_batch_id", "total_generated_batches", "dropped_batches", "slot_counts", "missing_samples", "dropped_batch_ranges", "loss_ranges_truncated", "raw_recording_enabled"}
            assert summary["cutoff_timestamp_ms"] == payload["timestamp_ms"]
            for name in ("cutoff_timestamp_ms", "total_generated_batches", "dropped_batches"):
                integer(summary[name])
            total = summary["total_generated_batches"]
            final = summary["final_batch_id"]
            assert (final is None and total == 0) or (type(final) is int and final >= 0 and final + 1 == total)
            assert summary["dropped_batches"] <= total
            counts(summary["slot_counts"])
            counts(summary["missing_samples"])
            assert all(summary["missing_samples"][s] <= summary["slot_counts"][s] for s in ("ppg", "imu", "gsr"))
            assert type(summary["loss_ranges_truncated"]) is bool
            assert type(summary["raw_recording_enabled"]) is bool
            ranges = summary["dropped_batch_ranges"]
            assert len(ranges) <= 64
            last = -1
            dropped = 0
            for item in ranges:
                assert set(item) == {"first", "last"}
                integer(item["first"])
                integer(item["last"])
                assert last < item["first"] <= item["last"] < total
                last = item["last"]
                dropped += item["last"] - item["first"] + 1
            if not summary["loss_ranges_truncated"]:
                assert dropped == summary["dropped_batches"]
    if kind == "PRESENCE":
        assert payload["status"] in {"ONLINE", "OFFLINE"}


def load_catalog():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert catalog["fixture_only"] is True
    resolved = {}
    for example in catalog["examples"]:
        name = example["id"]
        assert name not in resolved
        if "derive_from" in example:
            payload = copy.deepcopy(resolved[example["derive_from"]])
            for dotted, value in example["changes"].items():
                keys = dotted.split(".")
                target = payload
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
        else:
            payload = copy.deepcopy(example["payload"])
        resolved[name] = payload
    return catalog, resolved


def main():
    catalog, resolved = load_catalog()
    current_count = control_count = 0
    models = {"telemetry": Telemetry, "raw": RawBatch, "session_start": SessionStart, "session_stop": SessionStop}
    for example in catalog["examples"]:
        payload = resolved[example["id"]]
        try:
            if example["kind"] == "control":
                control(payload)
                assert example["topic_suffix"] == TOPICS[payload["message_type"]]
                assert example["qos"] == 1
                assert example["retain"] == (payload["message_type"] == "PRESENCE")
                control_count += 1
            else:
                valid = True
                try:
                    models[example["kind"]].model_validate(payload)
                except ValidationError:
                    valid = False
                assert valid == example["current_schema_valid"], "Unexpected current schema result"
                if "data_origin" in payload:
                    assert payload["data_origin"] == "SYNTHETIC"
                current_count += 1
        except (AssertionError, KeyError, TypeError) as error:
            raise AssertionError(f"Fixture {example['id']}: {error}") from error
    for name in ("raw_full", "raw_null_slots", "raw_final_partial"):
        payload = resolved[name]
        rate = payload["ppg"]["sample_rate_hz"]
        duration = len(payload["ppg"]["red"]) * 1000 / rate
        for stream, array in (("imu", "ax"), ("gsr", "adc")):
            assert len(payload[stream][array]) * 1000 / payload[stream]["sample_rate_hz"] == duration
    summary = resolved["ack_stopped"]["final_summary"]
    assert summary["cutoff_timestamp_ms"] == 1500
    assert summary["slot_counts"] == {"ppg": 15, "imu": 15, "gsr": 15}
    scenario_ids = [item["id"] for item in catalog["target_scenarios"]]
    assert len(scenario_ids) == len(set(scenario_ids))
    for scenario in catalog["target_scenarios"]:
        assert all(name in resolved for name in scenario.get("steps", []))
    negative_checks = 0
    for name, dotted, value in (
        ("command_start", "generation", 0),
        ("command_start", "generation", True),
        ("command_start", "expires_in_ms", 30001),
        ("command_start", "device_id", "../OTHER"),
        ("command_start", "debug", True),
        ("command_stop", "acquisition_profile", catalog["fixture_profile"]),
        ("ack_started", "timestamp_ms", 1),
        ("ack_stopped", "final_summary.total_generated_batches", 99),
        ("presence_online", "status", "RECORDING"),
    ):
        payload = copy.deepcopy(resolved[name])
        target = payload
        keys = dotted.split(".")
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        try:
            control(payload)
        except (AssertionError, KeyError, TypeError):
            negative_checks += 1
        else:
            raise AssertionError(f"Checker accepted negative fixture: {name}/{dotted}")
    print(f"PASS: {current_count} current-schema cases; {control_count} control fixture checks; raw timing/counts; {len(scenario_ids)} future scenario references.")
    print(f"PASS: {negative_checks} negative control fixture mutations rejected.")
    print("NOT RUN: broker/device/E2E, auth, durable storage, JCS vectors or lifecycle implementation.")


if __name__ == "__main__":
    main()

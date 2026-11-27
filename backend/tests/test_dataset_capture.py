import csv
import json
from pathlib import Path
from app.services.dataset_capture_service import DATASET_COLUMNS
from conftest import OP_HEADERS


def _make_samples(count: int, start_sec: int = 61, hr: float = 88.0, gsr: int = 1900):
    return [
        {
            "timestamp_ms": (start_sec + i) * 1000,
            "hr_bpm": hr + (i % 5) * 0.5,
            "gsr_raw": gsr + (i % 4) * 12,
            "gsr_delta": None,
            "ax": 0.1 * ((i % 3) - 1),
            "ay": 0.05,
            "az": 9.81,
            "gx": 0.2,
            "gy": -0.1,
            "gz": 0.05,
        }
        for i in range(count)
    ]


def test_dataset_capture_saves_exact_wesad_columns_and_windows(client, tmp_path):
    client.app.state.settings.collected_dataset_dir = str(tmp_path)

    resp = client.post(
        "/api/v1/dataset/captures",
        headers=OP_HEADERS,
        json={
            "device_id": "ESP32-001",
            "session_id": "AUTO-test1",
            "subject_id": "REAL_P01",
            "context": "stress_high",
            "label": 1,
            "samples": _make_samples(75),
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["saved"] is True
    assert body["batch_number"] == 1
    assert body["subject_id"] == "REAL_P01"
    assert body["context"] == "stress_high"
    assert body["sample_count"] == 75
    assert body["window_count"] == 3  # [0..60], [10..70], tail [15..75]
    assert body["label"] == 1
    assert body["raw_file"] == "raw_captures.jsonl"

    csv_file = Path(tmp_path) / "device_dataset.csv"
    assert csv_file.is_file()
    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0].keys()) == DATASET_COLUMNS
    assert len(rows) == 3
    assert rows[0]["subject_id"] == "REAL_P01"
    assert rows[0]["source_label_code"] == "2"
    assert rows[0]["label"] == "1"
    assert float(rows[0]["hr_is_valid"]) == 1.0

    raw_file = Path(tmp_path) / "raw_captures.jsonl"
    assert raw_file.is_file()
    raw_lines = [json.loads(line) for line in raw_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(raw_lines) == 1
    assert raw_lines[0]["subject_id"] == "REAL_P01"
    assert raw_lines[0]["context"] == "stress_high"
    assert len(raw_lines[0]["samples"]) == 75
    assert raw_lines[0]["samples"][0]["gx"] == 0.2


def test_dataset_capture_handles_short_post_calibration_segment_and_requires_auth(client, tmp_path):
    client.app.state.settings.collected_dataset_dir = str(tmp_path)

    unauth = client.post(
        "/api/v1/dataset/captures",
        json={"device_id": "ESP32-001", "label": 0, "samples": _make_samples(12)},
    )
    assert unauth.status_code == 401

    resp = client.post(
        "/api/v1/dataset/captures",
        headers=OP_HEADERS,
        json={"device_id": "ESP32-001", "label": 0, "samples": _make_samples(15)},
    )
    assert resp.status_code == 201
    assert resp.json()["window_count"] == 1
    assert resp.json()["label"] == 0


def test_dataset_capture_summary_reports_batch_number_previous_and_cumulative_samples(client, tmp_path):
    client.app.state.settings.collected_dataset_dir = str(tmp_path)

    empty = client.get("/api/v1/dataset/captures/summary", headers=OP_HEADERS)
    assert empty.status_code == 200
    assert empty.json() == {
        "completed_batches": 0,
        "next_batch_number": 1,
        "total_samples_before": 0,
        "last_subject_id": None,
        "known_subject_ids": [],
        "previous_batch": None,
    }

    client.post(
        "/api/v1/dataset/captures",
        headers=OP_HEADERS,
        json={"device_id": "ESP32-001", "subject_id": "REAL_P01", "context": "active", "label": 0, "samples": _make_samples(75)},
    )
    client.post(
        "/api/v1/dataset/captures",
        headers=OP_HEADERS,
        json={"device_id": "ESP32-001", "subject_id": "REAL_P02", "context": "stress_mild", "label": 1, "samples": _make_samples(20)},
    )

    summary = client.get("/api/v1/dataset/captures/summary", headers=OP_HEADERS)
    assert summary.status_code == 200
    assert summary.json() == {
        "completed_batches": 2,
        "next_batch_number": 3,
        "total_samples_before": 95,
        "last_subject_id": "REAL_P02",
        "known_subject_ids": ["REAL_P02", "REAL_P01"],
        "previous_batch": {
            "batch_number": 2,
            "duration_seconds": 20,
            "sample_count": 20,
            "label": 1,
            "subject_id": "REAL_P02",
            "context": "stress_mild",
        },
    }

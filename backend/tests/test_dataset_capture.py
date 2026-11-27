import csv
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
            "label": 1,
            "samples": _make_samples(75),
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["saved"] is True
    assert body["sample_count"] == 75
    assert body["window_count"] == 3  # [0..60], [10..70], tail [15..75]
    assert body["label"] == 1

    csv_file = Path(tmp_path) / "device_dataset.csv"
    assert csv_file.is_file()
    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0].keys()) == DATASET_COLUMNS
    assert len(rows) == 3
    assert rows[0]["subject_id"] == "REAL_ESP32-001"
    assert rows[0]["source_label_code"] == "2"
    assert rows[0]["label"] == "1"
    assert float(rows[0]["hr_is_valid"]) == 1.0


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

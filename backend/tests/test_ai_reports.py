from datetime import datetime, timedelta, timezone

from app.db.database import SessionLocal
from app.db.models import Event
from conftest import OP_HEADERS


def test_ai_reports_filter_before_limit_and_return_probability(client):
    base = datetime(2026, 11, 15, tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(Event(device_id="ESP-001", session_id=None, state="ATTENTION", probability=.73,
                     timestamp_ms=1000, created_at=base))
        # Unavailable predictions must not consume the report's 100-row limit.
        db.add_all(Event(device_id="ESP-001", session_id=None, state="UNCERTAIN", probability=None,
                         timestamp_ms=2000 + i, created_at=base + timedelta(seconds=i + 1)) for i in range(105))
        db.add(Event(device_id="ESP-001", session_id=None, state="ATTENTION", probability=None,
                     timestamp_ms=3000, created_at=base + timedelta(seconds=120)))
        db.add(Event(device_id="SIM-OTHER", session_id=None, state="ATTENTION", probability=.9,
                     timestamp_ms=4000, created_at=base + timedelta(seconds=121)))
        db.add(Event(device_id="ESP-001", session_id=None, state="NORMAL", probability=.1,
                     timestamp_ms=5000, created_at=base + timedelta(seconds=122)))
        db.commit()
    response = client.get("/api/v1/events?device_id=ESP-001&attention_only=true", headers=OP_HEADERS)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["state"] == "ATTENTION" and rows[0]["probability"] == .73
    assert rows[0]["timestamp_ms"] == 1000


def test_event_endpoint_keeps_existing_default_and_auth(client):
    with SessionLocal() as db:
        db.add(Event(device_id="ESP-001", session_id=None, state="UNCERTAIN", probability=None, timestamp_ms=1000))
        db.commit()
    assert client.get("/api/v1/events").status_code == 401
    rows = client.get("/api/v1/events", headers=OP_HEADERS).json()
    assert len(rows) == 1 and rows[0]["state"] == "UNCERTAIN"
    assert rows[0]["probability"] is None


def test_ai_report_paginates_groups_beyond_100_raw_records(client):
    base = datetime(2026, 11, 15, tzinfo=timezone.utc)
    with SessionLocal() as db:
        for group in range(25):
            for sample in range(5):
                second = group * 10 + sample
                db.add(Event(device_id="ESP-001", session_id="S-A", state="ATTENTION", probability=.5 + sample * .1,
                             timestamp_ms=second * 1000, created_at=base + timedelta(seconds=second)))
        db.commit()
    all_ids = []
    for page, expected in [(1, 10), (2, 10), (3, 5)]:
        response = client.get(f"/api/v1/reports/ai?device_id=ESP-001&page={page}", headers=OP_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25 and data["page"] == page and len(data["items"]) == expected
        assert all(row["record_count"] == 5 and row["reason"] is None and row["probability"] == .9 for row in data["items"])
        all_ids.extend(row["id"] for row in data["items"])
    assert len(set(all_ids)) == 25
    assert client.get("/api/v1/reports/ai?device_id=ESP-001&page=0", headers=OP_HEADERS).status_code == 422
    assert client.get("/api/v1/reports/ai?device_id=ESP-001").status_code == 401

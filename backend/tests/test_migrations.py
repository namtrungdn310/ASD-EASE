import sqlite3
from sqlalchemy import create_engine, inspect, text
from app.db.migrations import restore, upgrade
import pytest


def test_legacy_migration_backup_restore_and_idempotence(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.executescript("""CREATE TABLE sessions(session_id VARCHAR(64) PRIMARY KEY,device_id VARCHAR(64),
            participant_id VARCHAR(64),started_at DATETIME NOT NULL,stopped_at DATETIME);
            CREATE INDEX ix_sessions_device_id ON sessions(device_id);
            INSERT INTO sessions VALUES ('OLD','REAL-OR-SIM',NULL,'2026-10-01',NULL);
            CREATE TABLE devices(device_id VARCHAR(64) PRIMARY KEY,last_seen_at DATETIME,firmware_version VARCHAR(32),data_origin VARCHAR(16));
            INSERT INTO devices VALUES ('REAL-OR-SIM','2026-10-01','old','SYNTHETIC');""")
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    backup = upgrade(engine)
    assert backup.is_file()
    with engine.connect() as db:
        row = db.execute(text("SELECT * FROM sessions")).mappings().one()
        assert row["state"] == "LEGACY" and row["data_origin"] == "UNKNOWN"
        assert row["started_at"] == "2026-10-01" and not row["recording_complete"]
        assert "device_commands" in inspect(db).get_table_names()
    assert upgrade(engine) is None
    restored = tmp_path / "restored.db"
    restore(backup, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT session_id FROM sessions").fetchone() == ("OLD",)
        assert "state" not in [column[1] for column in db.execute("PRAGMA table_info(sessions)")]
    with pytest.raises(ValueError):
        restore(backup, path)
    engine.dispose()


def test_failed_migration_rolls_back_original_table(tmp_path):
    path = tmp_path / "broken-shape.db"
    with sqlite3.connect(path) as db:
        db.executescript("CREATE TABLE sessions(session_id TEXT PRIMARY KEY); INSERT INTO sessions VALUES ('KEEP');")
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with pytest.raises(Exception):
        upgrade(engine)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT session_id FROM sessions").fetchone() == ("KEEP",)
        assert db.execute("SELECT name FROM sqlite_master WHERE name='sessions_legacy_v0'").fetchone() is None
    assert len(list(tmp_path.glob("*.bak"))) == 1
    engine.dispose()

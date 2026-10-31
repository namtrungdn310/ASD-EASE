"""Nâng SQLite v0 lên v1; sao lưu trước thay đổi, không đoán nguồn phiên cũ."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from sqlalchemy import inspect, text
from app.db.database import Base
from app.db import models

VERSION = 1


def backup_database(engine):
    database = engine.url.database
    if not database or database == ":memory:" or not Path(database).is_file():
        return None
    source = Path(database).resolve()
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = source.with_name(source.name + f".v0-{suffix}.bak")
    with sqlite3.connect(source) as connection, sqlite3.connect(target) as backup:
        connection.backup(backup)
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Bản sao DB không toàn vẹn")
    return target


def upgrade(engine):
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Nhánh04 chỉ hỗ trợ migration SQLite đã kiểm thử")
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        if "schema_version" in tables:
            version = connection.execute(text("SELECT version FROM schema_version WHERE id=1")).scalar_one()
            if version != VERSION:
                raise RuntimeError("Phiên bản DB không được hỗ trợ")
            return None
    backup = backup_database(engine) if tables else None
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            if "sessions" in tables:
                connection.exec_driver_sql("ALTER TABLE sessions RENAME TO sessions_legacy_v0")
                connection.exec_driver_sql("DROP INDEX IF EXISTS ix_sessions_device_id")
                models.Session.__table__.create(connection)
                connection.exec_driver_sql("""INSERT INTO sessions
                    (session_id,device_id,participant_id,started_at,stopped_at,data_origin,state,
                    desired_state,actual_state,active,generation,recording_complete,empty_recording,incomplete_reasons_json)
                    SELECT session_id,device_id,participant_id,started_at,stopped_at,'UNKNOWN','LEGACY',
                    'UNKNOWN','UNKNOWN',0,0,0,0,'["LEGACY_UNKNOWN"]' FROM sessions_legacy_v0""")
                connection.exec_driver_sql("DROP TABLE sessions_legacy_v0")
            if "devices" in tables:
                for name, definition in {
                    "generation": "INTEGER NOT NULL DEFAULT 0", "boot_id": "VARCHAR(64)",
                    "connection_id": "VARCHAR(64)", "actual_state": "VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN'",
                    "sync_request_id": "VARCHAR(64)",
                    "last_telemetry_at": "DATETIME",
                    "unresolved": "BOOLEAN NOT NULL DEFAULT 0",
                }.items():
                    connection.exec_driver_sql(f"ALTER TABLE devices ADD COLUMN {name} {definition}")
                connection.exec_driver_sql("UPDATE devices SET last_telemetry_at=last_seen_at")
            Base.metadata.create_all(connection)
            connection.execute(text("INSERT INTO schema_version(id,version) VALUES (1,:version)"), {"version": VERSION})
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    return backup


def restore(backup, destination):
    backup, destination = Path(backup).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError("Chỉ khôi phục sang file mới, không ghi đè DB hiện có")
    with sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True) as source:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Bản sao hỏng")
        with sqlite3.connect(destination) as target:
            source.backup(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--to", type=Path)
    arguments = parser.parse_args()
    if not arguments.restore or not arguments.to:
        parser.error("Dùng --restore <bản sao> --to <DB mới>; dừng backend trước")
    restore(arguments.restore, arguments.to)

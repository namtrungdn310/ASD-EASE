from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    firmware_version: Mapped[str] = mapped_column(String(32))
    data_origin: Mapped[str] = mapped_column(String(16))
    last_telemetry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    boot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    connection_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actual_state: Mapped[str] = mapped_column(String(20), default="UNKNOWN", server_default="UNKNOWN")
    unresolved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class Session(Base):
    __tablename__ = "sessions"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    participant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_origin: Mapped[str] = mapped_column(String(16), default="UNKNOWN", server_default="UNKNOWN")
    state: Mapped[str] = mapped_column(String(20), default="LEGACY", server_default="LEGACY")
    desired_state: Mapped[str] = mapped_column(String(20), default="UNKNOWN", server_default="UNKNOWN")
    actual_state: Mapped[str] = mapped_column(String(20), default="UNKNOWN", server_default="UNKNOWN")
    active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    command_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    boot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acquisition_profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    cutoff_timestamp_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drain_deadline_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recording_complete: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    empty_recording: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    incomplete_reasons_json: Mapped[str] = mapped_column(Text, default='["LEGACY_UNKNOWN"]', server_default='["LEGACY_UNKNOWN"]')
    __table_args__ = (Index("uq_open_session_device", "device_id", unique=True, sqlite_where=text("active = 1")),)


class DeviceCommand(Base):
    __tablename__ = "device_commands"
    command_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    generation: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(8))
    boot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    ack_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class CommandLease(Base):
    __tablename__ = "command_leases"
    lease_id: Mapped[str] = mapped_column(String(220), primary_key=True)
    command_id: Mapped[str] = mapped_column(String(64), index=True)
    boot_id: Mapped[str] = mapped_column(String(64))
    connection_id: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(64))
    expires_at_ms: Mapped[int] = mapped_column(Integer)


class DeviceConnection(Base):
    __tablename__ = "device_connections"
    identity: Mapped[str] = mapped_column(String(200), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    boot_id: Mapped[str] = mapped_column(String(64))
    connection_id: Mapped[str] = mapped_column(String(64))


class TelemetryCursor(Base):
    __tablename__ = "telemetry_cursors"
    identity: Mapped[str] = mapped_column(String(150), primary_key=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    digest: Mapped[str] = mapped_column(String(64))


class SyncNonce(Base):
    __tablename__ = "sync_nonces"
    identity: Mapped[str] = mapped_column(String(264), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    connection_id: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(64))
    received_at_ms: Mapped[int] = mapped_column(Integer)


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer)


class Annotation(Base):
    __tablename__ = "annotations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(20))
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


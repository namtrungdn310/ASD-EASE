from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String, Text
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


class Session(Base):
    __tablename__ = "sessions"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    participant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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


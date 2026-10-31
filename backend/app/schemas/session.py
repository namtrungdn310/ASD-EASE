from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.control import AcquisitionProfile, Identifier


class SessionStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: Identifier
    device_id: Identifier
    participant_id: Identifier | None = None


class SessionStop(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: Identifier


class SessionResponse(BaseModel):
    session_id: str
    device_id: str
    participant_id: str | None
    data_origin: str
    state: str
    desired_state: str
    actual_state: str
    command_id: str | None
    generation: int
    boot_id: str | None
    requested_at: datetime | None
    started_at: datetime | None
    stopped_at: datetime | None
    cutoff_timestamp_ms: int | None
    final_batch_id: int | None
    recording_complete: bool
    empty_recording: bool
    incomplete_reasons: list[str]
    acquisition_profile: AcquisitionProfile | None


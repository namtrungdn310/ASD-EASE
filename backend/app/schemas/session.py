from datetime import datetime
from pydantic import BaseModel, Field


class SessionStart(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=64)
    participant_id: str | None = Field(default=None, max_length=64)


class SessionStop(BaseModel):
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    device_id: str
    participant_id: str | None
    started_at: datetime
    stopped_at: datetime | None


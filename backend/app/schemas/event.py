from datetime import datetime
from pydantic import BaseModel


class EventResponse(BaseModel):
    id: int
    device_id: str
    session_id: str | None
    state: str
    timestamp_ms: int
    created_at: datetime


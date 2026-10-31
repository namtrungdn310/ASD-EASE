from pydantic import BaseModel, ConfigDict, Field
from app.schemas.control import Counter, Identifier


class AnnotationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: Identifier
    timestamp_ms: Counter
    label: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=1000)


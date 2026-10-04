from pydantic import BaseModel, Field


class AnnotationCreate(BaseModel):
    session_id: str
    timestamp_ms: int = Field(ge=0)
    label: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=1000)


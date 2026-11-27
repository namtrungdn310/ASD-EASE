from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.core.security import operator_auth
from app.services.dataset_capture_service import get_capture_summary, save_labeled_capture

router = APIRouter(tags=["dataset capture"], dependencies=[Depends(operator_auth)])


class CaptureSample(BaseModel):
    timestamp_ms: int = Field(ge=0)
    hr_bpm: float | None = Field(default=None, ge=20, le=240)
    gsr_raw: int | None = Field(default=None, ge=0, le=4095)
    gsr_delta: float | None = None
    ax: float | None = None
    ay: float | None = None
    az: float | None = None


class CaptureCreateRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    session_id: str | None = Field(default=None, max_length=64)
    label: Literal[0, 1]
    samples: list[CaptureSample] = Field(min_length=5, max_length=7200)


@router.get("/dataset/captures/summary")
def read_dataset_capture_summary(request: Request):
    settings = request.app.state.settings
    output_dir = Path(settings.collected_dataset_dir)
    return get_capture_summary(output_dir=output_dir)


@router.post("/dataset/captures", status_code=status.HTTP_201_CREATED)
def create_dataset_capture(body: CaptureCreateRequest, request: Request):
    settings = request.app.state.settings
    output_dir = Path(settings.collected_dataset_dir)
    return save_labeled_capture(
        output_dir=output_dir,
        device_id=body.device_id,
        session_id=body.session_id,
        label=body.label,
        samples=[sample.model_dump() for sample in body.samples],
    )

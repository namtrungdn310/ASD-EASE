"""Điểm chất lượng kỹ thuật 1.2; không phải xác suất HR/giá trị đo đúng."""
from typing import Annotated, Literal

from pydantic import Field, StrictFloat, StrictInt, model_serializer, model_validator

from app.schemas.control import WireModel
from app.schemas.imu import TelemetryV11


class QualityReading(WireModel):
    sample_count: Annotated[StrictInt, Field(ge=0, le=9007199254740991)] | None = None
    score: Annotated[StrictInt | StrictFloat, Field(ge=0, le=1)] | None
    reason: Literal["ok", "warming_up", "stale", "no_contact", "motion", "saturated",
                    "missing_samples", "weak_signal", "calibrating", "unavailable"]

    @model_serializer(mode="wrap")
    def keep_legacy_shape(self, handler):
        data = handler(self)
        if "sample_count" not in self.model_fields_set:
            data.pop("sample_count", None)
        return data

    @model_validator(mode="after")
    def score_matches_availability(self):
        unknown = self.reason in {"warming_up", "stale", "calibrating", "unavailable"}
        if unknown != (self.score is None):
            raise ValueError("Điểm phải null khi chưa đánh giá hoặc mẫu không còn mới")
        return self


class MetricQuality(WireModel):
    method: Literal["engineering-v1", "engineering-v2"]
    window_ms: Annotated[StrictInt, Field(ge=8000, le=8000)]
    hr: QualityReading
    gsr: QualityReading
    acceleration: QualityReading
    rotation: QualityReading


class TelemetryV12(TelemetryV11):
    schema_version: Literal["1.2"]
    signal_quality: MetricQuality

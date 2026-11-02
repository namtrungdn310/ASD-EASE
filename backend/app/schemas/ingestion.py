"""Kiểm tra telemetry chung HTTP/MQTT, giữ schema người dùng làm tương thích."""
from typing import Annotated, Literal
from pydantic import Field, StrictFloat, StrictInt, model_validator
from app.schemas.control import Counter, Identifier, WireModel
from app.schemas.telemetry import Telemetry

Number = StrictInt | StrictFloat
Unit = Annotated[Number, Field(ge=0, le=1)]


class GSR(WireModel):
    raw: Annotated[int, Field(strict=True, ge=0, le=4095)] | None = None
    delta: Number | None = None


class Movement(WireModel):
    score: Unit | None = None


class Quality(WireModel):
    ppg: Unit
    imu: Unit
    gsr: Unit


class Prediction(WireModel):
    probability: Unit | None = None
    state: Literal["NORMAL", "ATTENTION", "UNCERTAIN", "CALIBRATING"]


class InboundTelemetry(WireModel):
    schema_version: Literal["1.0"]
    device_id: Identifier
    session_id: Identifier | None = None
    timestamp_ms: Counter
    data_origin: Literal["DEVICE", "SYNTHETIC"]
    hr_bpm: Annotated[Number, Field(ge=20, le=240)] | None = None
    gsr: GSR
    movement: Movement
    signal_quality: Quality
    prediction: Prediction
    firmware_version: str = Field(min_length=1, max_length=64)
    model_version: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def no_fabricated_device_prediction(self):
        if self.data_origin == "DEVICE" and self.model_version == "none":
            if self.prediction.probability is not None or self.prediction.state not in {"UNCERTAIN", "CALIBRATING"}:
                raise ValueError("DEVICE chưa có mô hình không được tự gán dự đoán")
        return self

    def telemetry(self):
        return Telemetry.model_validate(self.model_dump())

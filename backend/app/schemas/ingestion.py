"""Kiểm tra telemetry chung HTTP/MQTT, giữ schema người dùng làm tương thích."""
from typing import Annotated, Literal
from pydantic import Field, StrictFloat, StrictInt, model_validator
from app.schemas.control import Counter, Identifier, WireModel
from app.schemas.telemetry import Telemetry
from app.schemas.imu import AxisVector, TelemetryV11
from app.schemas.quality import MetricQuality, TelemetryV12

Number = StrictInt | StrictFloat
Unit = Annotated[Number, Field(ge=0, le=1)]


class GSR(WireModel):
    raw: Annotated[int, Field(strict=True, ge=0, le=4095)] | None = None
    delta: Number | None = None


class Movement(WireModel):
    score: Unit | None = None


class MovementV11(Movement):
    acceleration: AxisVector | None
    angular_velocity: AxisVector | None


class Quality(WireModel):
    ppg: Unit
    imu: Unit
    gsr: Unit


class Prediction(WireModel):
    probability: Unit | None = None
    state: Literal["NORMAL", "ATTENTION", "UNCERTAIN", "CALIBRATING"]


class InboundTelemetry(WireModel):
    schema_version: Literal["1.0", "1.1", "1.2"]
    device_id: Identifier
    session_id: Identifier | None = None
    timestamp_ms: Counter
    data_origin: Literal["DEVICE", "SYNTHETIC"]
    hr_bpm: Annotated[Number, Field(ge=20, le=240)] | None = None
    gsr: GSR
    movement: Movement | MovementV11
    signal_quality: Quality | MetricQuality
    prediction: Prediction
    firmware_version: str = Field(min_length=1, max_length=64)
    model_version: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def no_fabricated_device_prediction(self):
        if (self.schema_version != "1.0") != isinstance(self.movement, MovementV11):
            raise ValueError("Telemetry1.1 cần acceleration/angular_velocity; telemetry1.0 không có hai trường này")
        if (self.schema_version == "1.2") != isinstance(self.signal_quality, MetricQuality):
            raise ValueError("Telemetry1.2 cần điểm chất lượng engineering-v1/v2; bản cũ giữ cấu trúc cũ")
        if self.data_origin == "DEVICE" and self.model_version == "none":
            if self.prediction.probability is not None or self.prediction.state not in {"UNCERTAIN", "CALIBRATING"}:
                raise ValueError("DEVICE chưa có mô hình không được tự gán dự đoán")
        return self

    def telemetry(self):
        model = {"1.0": Telemetry, "1.1": TelemetryV11, "1.2": TelemetryV12}[self.schema_version]
        return model.model_validate(self.model_dump())

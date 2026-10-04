from pydantic import BaseModel, ConfigDict, Field
from app.core.enums import DataOrigin, EngineeringState


class GSRReading(BaseModel):
    raw: int | None = Field(default=None, ge=0, le=4095)
    delta: float | None = None


class MovementReading(BaseModel):
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class SignalQuality(BaseModel):
    ppg: float = Field(ge=0.0, le=1.0)
    gsr: float = Field(ge=0.0, le=1.0)
    imu: float = Field(ge=0.0, le=1.0)


class Prediction(BaseModel):
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    state: EngineeringState


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(pattern=r"^1\.0$")
    device_id: str = Field(min_length=1, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)
    timestamp_ms: int = Field(ge=0)
    data_origin: DataOrigin = DataOrigin.DEVICE
    hr_bpm: float | None = Field(default=None, ge=20.0, le=240.0)
    gsr: GSRReading
    movement: MovementReading
    signal_quality: SignalQuality
    prediction: Prediction
    firmware_version: str
    model_version: str


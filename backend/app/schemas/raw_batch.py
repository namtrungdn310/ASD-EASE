from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.enums import DataOrigin


Sample = int | float | None


class PPGStream(BaseModel):
    sample_rate_hz: float = Field(gt=0, le=1000)
    red: list[Sample]
    ir: list[Sample]

    @model_validator(mode="after")
    def equal_lengths(self):
        if len(self.red) != len(self.ir):
            raise ValueError("PPG red and IR arrays must have equal lengths")
        return self


class IMUStream(BaseModel):
    sample_rate_hz: float = Field(gt=0, le=1000)
    ax: list[Sample]
    ay: list[Sample]
    az: list[Sample]
    gx: list[Sample]
    gy: list[Sample]
    gz: list[Sample]

    @model_validator(mode="after")
    def equal_lengths(self):
        lengths = {len(v) for v in (self.ax, self.ay, self.az, self.gx, self.gy, self.gz)}
        if len(lengths) > 1:
            raise ValueError("All IMU arrays must have equal lengths")
        return self


class GSRStream(BaseModel):
    sample_rate_hz: float = Field(gt=0, le=1000)
    adc: list[Sample]


class RawBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(pattern=r"^1\.0$")
    device_id: str
    session_id: str
    batch_id: int = Field(ge=0)
    start_timestamp_ms: int = Field(ge=0)
    data_origin: DataOrigin = DataOrigin.DEVICE
    ppg: PPGStream
    imu: IMUStream
    gsr: GSRStream


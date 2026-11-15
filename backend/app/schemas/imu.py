"""Telemetry1.1: gia tốc m/s² và vận tốc góc degrees/s, theo hệ trục driver."""
from typing import Literal
from pydantic import ConfigDict, StrictFloat
from app.schemas.control import WireModel
from app.schemas.telemetry import MovementReading, Telemetry


class AxisVector(WireModel):
    x: StrictFloat
    y: StrictFloat
    z: StrictFloat


class MovementReadingV11(MovementReading):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    acceleration: AxisVector | None
    angular_velocity: AxisVector | None


class TelemetryV11(Telemetry):
    schema_version: Literal["1.1"]
    movement: MovementReadingV11

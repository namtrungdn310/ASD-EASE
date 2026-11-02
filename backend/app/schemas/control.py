"""Gói điều khiển MQTT 1.0; kiểm tra cấu trúc trước khi đổi trạng thái."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_INTEGER = 2**53 - 1
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
Counter = Annotated[int, Field(strict=True, ge=0, le=MAX_INTEGER)]
Generation = Annotated[int, Field(strict=True, ge=1, le=MAX_INTEGER)]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class AcquisitionProfile(WireModel):
    ppg_hz: Annotated[int, Field(strict=True, ge=1, le=1000)] = 50
    imu_hz: Annotated[int, Field(strict=True, ge=1, le=1000)] = 50
    gsr_hz: Annotated[int, Field(strict=True, ge=1, le=1000)] = 20
    window_ms: Annotated[int, Field(strict=True, ge=1000, le=1000)] = 1000


class Counts(WireModel):
    ppg: Counter
    imu: Counter
    gsr: Counter


class BatchRange(WireModel):
    first: Counter
    last: Counter


class FinalSummary(WireModel):
    cutoff_timestamp_ms: Counter
    final_batch_id: Counter | None
    total_generated_batches: Counter
    dropped_batches: Counter
    slot_counts: Counts
    missing_samples: Counts
    dropped_batch_ranges: list[BatchRange] = Field(max_length=64)
    loss_ranges_truncated: bool = Field(strict=True)
    raw_recording_enabled: bool = Field(strict=True)

    @model_validator(mode="after")
    def consistent(self):
        total = self.total_generated_batches
        if (total == 0 and self.final_batch_id is not None) or (total > 0 and self.final_batch_id != total - 1):
            raise ValueError("final_batch_id/total không khớp")
        if self.dropped_batches > total:
            raise ValueError("Số batch bỏ vượt tổng")
        previous, dropped = -1, 0
        for item in self.dropped_batch_ranges:
            if not previous < item.first <= item.last < total:
                raise ValueError("Khoảng mất batch sai thứ tự/giới hạn")
            previous = item.last
            dropped += item.last - item.first + 1
        if dropped > self.dropped_batches or (not self.loss_ranges_truncated and dropped != self.dropped_batches):
            raise ValueError("Tổng khoảng mất không khớp")
        if any(getattr(self.missing_samples, name) > getattr(self.slot_counts, name) for name in ("ppg", "imu", "gsr")):
            raise ValueError("Số mẫu thiếu vượt số vị trí")
        if total == 0 and (self.cutoff_timestamp_ms or any(self.slot_counts.model_dump().values())):
            raise ValueError("Phiên không batch phải có cutoff/counts bằng0")
        return self


class Envelope(WireModel):
    control_version: Literal["1.0"]
    device_id: Identifier
    data_origin: Literal["DEVICE", "SYNTHETIC"]
    boot_id: Identifier
    connection_id: Identifier


class Command(Envelope):
    message_type: Literal["COMMAND"]
    request_id: Identifier
    command_id: Identifier
    generation: Generation
    session_id: Identifier
    action: Literal["START", "STOP"]
    expires_in_ms: Annotated[int, Field(strict=True, ge=1, le=30000)]
    acquisition_profile: AcquisitionProfile | None

    @model_validator(mode="after")
    def profile_matches_action(self):
        if (self.action == "START") != (self.acquisition_profile is not None):
            raise ValueError("START cần profile; STOP dùng null")
        return self


class Ack(Envelope):
    message_type: Literal["ACK"]
    request_id: Identifier
    command_id: Identifier
    generation: Generation
    session_id: Identifier
    action: Literal["START", "STOP"]
    result: Literal["STARTED", "STOPPED", "REJECTED"]
    timestamp_ms: Counter
    reason: Identifier | None
    final_summary: FinalSummary | None

    @model_validator(mode="after")
    def result_matches_action(self):
        if self.result == "STARTED":
            valid = self.action == "START" and self.timestamp_ms == 0 and self.reason is None and self.final_summary is None
        elif self.result == "STOPPED":
            valid = self.action == "STOP" and self.reason is None and self.final_summary is not None
            if valid:
                valid = self.timestamp_ms == self.final_summary.cutoff_timestamp_ms
        else:
            valid = self.reason is not None and self.final_summary is None
        if not valid:
            raise ValueError("Kết quả ACK không khớp action/summary")
        return self


class StateRequest(Envelope):
    message_type: Literal["STATE_REQUEST"]
    request_id: Identifier
    actual_state: Literal["IDLE", "RECORDING", "STOPPED"]
    session_id: Identifier | None
    last_command_id: Identifier | None
    last_generation: Counter
    timestamp_ms: Counter
    last_ack: Ack | None

    @model_validator(mode="after")
    def state_has_session(self):
        if self.actual_state == "RECORDING" and self.session_id is None:
            raise ValueError("RECORDING cần session_id")
        return self


class StateResponse(Envelope):
    message_type: Literal["STATE_RESPONSE"]
    request_id: Identifier
    session_id: Identifier | None
    state: Literal["IDLE", "STARTING", "RECORDING", "STOPPING", "STOPPED", "ABORTED"]
    generation: Counter
    accepted_command_id: Identifier | None
    pending_command: Command | None
    error_code: Identifier | None


class Presence(Envelope):
    message_type: Literal["PRESENCE"]
    status: Literal["ONLINE", "OFFLINE"]

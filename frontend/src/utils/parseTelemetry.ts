import type {Telemetry} from "../types/telemetry";
import {
  isRecord,
  isFiniteNumber,
  isNumberInRange,
} from "./validation";

export function isTelemetry(value: unknown): value is Telemetry {
  if (!isRecord(value)) {
    return false;
  }

  const {
    gsr,
    movement,
    signal_quality: quality,
    prediction,
  } = value;

  if (
    !isRecord(gsr) ||
    !isRecord(movement) ||
    !isRecord(quality) ||
    !isRecord(prediction)
  ) {
    return false;
  }

  return (
    value.schema_version === "1.0" &&
    typeof value.device_id === "string" &&
    value.device_id.length > 0 &&
    value.device_id.length <= 64 &&
    (
      value.session_id === null ||
      (
        typeof value.session_id === "string" &&
        value.session_id.length <= 64
      )
    ) &&
    isNumberInRange(value.timestamp_ms, 0, Number.MAX_SAFE_INTEGER) &&
    Number.isInteger(value.timestamp_ms) &&
    (
      value.data_origin === "DEVICE" ||
      value.data_origin === "SYNTHETIC"
    ) &&
    (
      value.hr_bpm === null ||
      isNumberInRange(value.hr_bpm, 20, 240)
    ) &&
    (
      gsr.raw === null ||
      (
        isNumberInRange(gsr.raw, 0, 4095) &&
        Number.isInteger(gsr.raw)
      )
    ) &&
    (gsr.delta === null || isFiniteNumber(gsr.delta)) &&
    (
      movement.score === null ||
      isNumberInRange(movement.score, 0, 1)
    ) &&
    isNumberInRange(quality.ppg, 0, 1) &&
    isNumberInRange(quality.gsr, 0, 1) &&
    isNumberInRange(quality.imu, 0, 1) &&
    (
      prediction.probability === null ||
      isNumberInRange(prediction.probability, 0, 1)
    ) &&
    (
      prediction.state === "NORMAL" ||
      prediction.state === "ATTENTION" ||
      prediction.state === "UNCERTAIN" ||
      prediction.state === "CALIBRATING"
    ) &&
    typeof value.firmware_version === "string" &&
    typeof value.model_version === "string"
  );
}

export function parseTelemetry(text: string): Telemetry | null {
  try {
    const value: unknown = JSON.parse(text);
    return isTelemetry(value) ? value : null;
  } catch {
    return null;
  }
}
import type {Telemetry} from "../types/telemetry";
import {
  isRecord,
  isFiniteNumber,
  isNumberInRange,
} from "./validation";

function isAxisVector(value: unknown): boolean {
  return value === null || (isRecord(value) && Object.keys(value).length === 3 &&
    isFiniteNumber(value.x) && isFiniteNumber(value.y) && isFiniteNumber(value.z));
}

function isMetricQuality(value: Record<string, unknown>): boolean {
  if (Object.keys(value).length !== 6 || !["engineering-v1", "engineering-v2"].includes(String(value.method)) || value.window_ms !== 8000) return false;
  return ["hr", "gsr", "acceleration", "rotation"].every(key => {
    const reading = value[key];
    if (!isRecord(reading) || !Object.keys(reading).every(key => ["score", "reason", "sample_count"].includes(key)) || typeof reading.reason !== "string") return false;
    if (reading.sample_count !== undefined && reading.sample_count !== null &&
      !(isFiniteNumber(reading.sample_count) && Number.isSafeInteger(reading.sample_count) && reading.sample_count >= 0)) return false;
    const unavailable = ["warming_up", "stale", "calibrating", "unavailable"].includes(reading.reason);
    const available = ["ok", "no_contact", "motion", "saturated", "missing_samples", "weak_signal"].includes(reading.reason);
    return (unavailable && reading.score === null) || (available && isNumberInRange(reading.score, 0, 1));
  });
}

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
    (
      (value.schema_version === "1.0" && !("acceleration" in movement) && !("angular_velocity" in movement)) ||
      ((value.schema_version === "1.1" || value.schema_version === "1.2") && isAxisVector(movement.acceleration) && isAxisVector(movement.angular_velocity))
    ) &&
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
    (value.schema_version === "1.2" ? isMetricQuality(quality) :
      Object.keys(quality).length === 3 && isNumberInRange(quality.ppg, 0, 1) &&
      isNumberInRange(quality.gsr, 0, 1) && isNumberInRange(quality.imu, 0, 1)) &&
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

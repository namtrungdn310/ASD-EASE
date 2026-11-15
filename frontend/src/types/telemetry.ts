export type EngineeringState = "NORMAL" | "ATTENTION" | "UNCERTAIN" | "CALIBRATING";
export type DataOrigin = "DEVICE" | "SYNTHETIC";

export interface AxisVector {
  x: number;
  y: number;
  z: number;
}

export type QualityReason = "ok" | "warming_up" | "stale" | "no_contact" | "motion" |
  "saturated" | "missing_samples" | "weak_signal" | "calibrating" | "unavailable";
export interface QualityReading { score: number | null; reason: QualityReason; sample_count?: number | null }
export interface MetricQuality {
  method: "engineering-v1" | "engineering-v2";
  window_ms: 8000;
  hr: QualityReading;
  gsr: QualityReading;
  acceleration: QualityReading;
  rotation: QualityReading;
}
export interface LegacyQuality { ppg: number; gsr: number; imu: number }

interface TelemetryBase {
  device_id: string;
  session_id: string | null;
  timestamp_ms: number;
  data_origin: DataOrigin;
  hr_bpm: number | null;
  gsr: {raw: number | null; delta: number | null};
  prediction: {probability: number | null; state: EngineeringState};
  firmware_version: string;
  model_version: string;
}

export type Telemetry = TelemetryBase & (
  | { schema_version: "1.0"; signal_quality: LegacyQuality; movement: { score: number | null } }
  | { schema_version: "1.1"; signal_quality: LegacyQuality; movement: {
      score: number | null;
      acceleration: AxisVector | null;
      angular_velocity: AxisVector | null;
    } }
  | { schema_version: "1.2"; signal_quality: MetricQuality; movement: {
      score: number | null;
      acceleration: AxisVector | null;
      angular_velocity: AxisVector | null;
    } }
);

export interface ChartPoint {
  time: number;
  hr: number | null;
  gsr: number | null;
  movement: number | null;
  ax: number | null;
  ay: number | null;
  az: number | null;
  gx: number | null;
  gy: number | null;
  gz: number | null;
  probability: number | null;
}


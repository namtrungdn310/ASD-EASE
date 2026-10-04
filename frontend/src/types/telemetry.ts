export type EngineeringState = "NORMAL" | "ATTENTION" | "UNCERTAIN" | "CALIBRATING";
export type DataOrigin = "DEVICE" | "SYNTHETIC";

export interface Telemetry {
  schema_version: "1.0";
  device_id: string;
  session_id: string | null;
  timestamp_ms: number;
  data_origin: DataOrigin;
  hr_bpm: number | null;
  gsr: {raw: number | null; delta: number | null};
  movement: {score: number | null};
  signal_quality: {ppg: number; gsr: number; imu: number};
  prediction: {probability: number | null; state: EngineeringState};
  firmware_version: string;
  model_version: string;
}

export interface ChartPoint {
  time: number;
  hr: number | null;
  gsr: number | null;
  movement: number | null;
  probability: number | null;
}


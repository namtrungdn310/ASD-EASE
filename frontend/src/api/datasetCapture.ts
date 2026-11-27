import { API_BASE_URL } from "./index";
import { openLocalSession } from "../utils/localSession";

export interface CaptureSamplePayload {
  timestamp_ms: number;
  hr_bpm: number | null;
  gsr_raw: number | null;
  gsr_delta: number | null;
  ax: number | null;
  ay: number | null;
  az: number | null;
  gx: number | null;
  gy: number | null;
  gz: number | null;
}

export type CaptureContext = "rest" | "active" | "stress_mild" | "stress_high";

export interface DatasetCaptureRequest {
  device_id: string;
  session_id: string | null;
  subject_id?: string | null;
  context?: CaptureContext | null;
  label: 0 | 1;
  samples: CaptureSamplePayload[];
}

export interface DatasetCaptureResponse {
  saved: boolean;
  batch_number: number;
  device_id: string;
  subject_id: string;
  context: string;
  label: 0 | 1;
  sample_count: number;
  window_count: number;
  duration_seconds: number;
  dataset_file: string;
  raw_file: string;
}

export interface PreviousBatchSummary {
  batch_number: number;
  duration_seconds: number;
  sample_count: number;
  label: 0 | 1;
  subject_id?: string | null;
  context?: string | null;
}

export interface DatasetCaptureSummary {
  completed_batches: number;
  next_batch_number: number;
  total_samples_before: number;
  last_subject_id: string | null;
  known_subject_ids: string[];
  previous_batch: PreviousBatchSummary | null;
}

const base = API_BASE_URL.replace(/\/$/, "");
const apiRoot = () => (base.endsWith("/api/v1") ? base : `${base}/api/v1`);

export async function fetchDatasetCaptureSummary(): Promise<DatasetCaptureSummary> {
  const url = `${apiRoot()}/dataset/captures/summary`;
  const send = () =>
    fetch(url, {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    });

  let response = await send();
  if (response.status === 401 && import.meta.env.DEV) {
    await openLocalSession(new AbortController().signal);
    response = await send();
  }
  if (!response.ok) {
    throw new Error(`CAPTURE_SUMMARY_FAILED_${response.status}`);
  }
  return (await response.json()) as DatasetCaptureSummary;
}

export async function saveDatasetCapture(payload: DatasetCaptureRequest): Promise<DatasetCaptureResponse> {
  const url = `${apiRoot()}/dataset/captures`;
  const send = () =>
    fetch(url, {
      method: "POST",
      credentials: "include",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

  let response = await send();
  if (response.status === 401 && import.meta.env.DEV) {
    await openLocalSession(new AbortController().signal);
    response = await send();
  }
  if (!response.ok) {
    throw new Error(`CAPTURE_SAVE_FAILED_${response.status}`);
  }
  return (await response.json()) as DatasetCaptureResponse;
}

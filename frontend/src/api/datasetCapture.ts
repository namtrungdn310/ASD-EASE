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
}

export interface DatasetCaptureRequest {
  device_id: string;
  session_id: string | null;
  label: 0 | 1;
  samples: CaptureSamplePayload[];
}

export interface DatasetCaptureResponse {
  saved: boolean;
  device_id: string;
  label: 0 | 1;
  sample_count: number;
  window_count: number;
  duration_seconds: number;
  dataset_file: string;
}

const base = API_BASE_URL.replace(/\/$/, "");
const apiRoot = () => (base.endsWith("/api/v1") ? base : `${base}/api/v1`);

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

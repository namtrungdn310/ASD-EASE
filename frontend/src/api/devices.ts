import { API_BASE_URL } from "./index";
import { openLocalSession } from "../utils/localSession";

export interface DeviceOption { device_id: string; last_seen_at: string | null }
export const isDeviceId = (value: unknown): value is string => typeof value === "string" &&
  /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(value);
const base = API_BASE_URL.replace(/\/$/, "");
const apiRoot = () => (base.endsWith("/api/v1") ? base : `${base}/api/v1`);

export async function listDevices(signal: AbortSignal): Promise<DeviceOption[]> {
  const response = await fetch(`${apiRoot()}/devices`, {
    method: "GET", credentials: "include", cache: "no-store", signal,
  });
  if (!response.ok) throw new Error("DEVICES_UNAVAILABLE");
  const data: unknown = await response.json();
  if (!Array.isArray(data)) throw new Error("DEVICES_INVALID");
  if (!data.every(row => row && isDeviceId(row.device_id) && ['DEVICE', 'SYNTHETIC'].includes(row.data_origin) &&
    (row.last_seen_at === null || typeof row.last_seen_at === "string" && Number.isFinite(Date.parse(row.last_seen_at)))))
    throw new Error("DEVICES_INVALID");
  return data.filter(row => row.data_origin === 'DEVICE').map(row => ({ device_id: row.device_id, last_seen_at: row.last_seen_at }))
    .sort((a, b) => (Date.parse(b.last_seen_at ?? "") || 0) - (Date.parse(a.last_seen_at ?? "") || 0) || a.device_id.localeCompare(b.device_id));
}

export async function resetDeviceAi(deviceId: string, signal?: AbortSignal): Promise<void> {
  const url = `${apiRoot()}/devices/${encodeURIComponent(deviceId)}/ai-reset`;
  const send = () => fetch(url, { method: "POST", credentials: "include", cache: "no-store", signal });
  let response = await send();
  if (response.status === 401 && import.meta.env.DEV) {
    await openLocalSession(signal ?? new AbortController().signal);
    response = await send();
  }
  if (!response.ok) {
    let detail = "";
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch { /* bỏ qua lỗi phân tích phản hồi */ }
    throw new Error(detail || `AI_RESET_FAILED_${response.status}`);
  }
}

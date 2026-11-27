import { openLocalSession } from "../utils/localSession";

export interface AiEvent {
  id: number;
  device_id: string;
  session_id: string | null;
  state: "ATTENTION";
  probability: number;
  timestamp_ms: number;
  created_at: string;
  ended_at: string;
  record_count: number;
  reason: string | null;
}

export interface AiReportPage { items: AiEvent[]; total: number; page: number; page_size: number }

export function eventTime(value: string): number {
  // SQLite có thể trả UTC không kèm hậu tố múi giờ.
  return Date.parse(/[zZ]$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
}

export async function listAiReportPage(deviceId: string, page: number, signal: AbortSignal): Promise<AiReportPage> {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const url = new URL(`${base}/api/v1/reports/ai`);
  url.searchParams.set("device_id", deviceId);
  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", "10");
  const send = () => fetch(url, { credentials: "include", cache: "no-store", signal });
  let response = await send();
  if (response.status === 401 && import.meta.env.DEV) {
    await openLocalSession(signal ?? new AbortController().signal);
    response = await send();
  }
  if (!response.ok) throw new Error("Không tải được báo cáo. Kiểm tra kết nối backend.");
  const data: unknown = await response.json();
  if (data === null || typeof data !== "object" || !("items" in data) || !Array.isArray(data.items) ||
      !("total" in data) || !Number.isSafeInteger(data.total) || Number(data.total) < 0 ||
      !("page" in data) || data.page !== page || !("page_size" in data) || data.page_size !== 10) {
    throw new Error("Dữ liệu báo cáo không hợp lệ.");
  }
  const items = data.items.filter((item): item is AiEvent => item !== null && typeof item === "object" &&
    Number.isInteger(item.id) && item.device_id === deviceId && item.state === "ATTENTION" &&
    (item.session_id === null || typeof item.session_id === "string") &&
    typeof item.probability === "number" && Number.isFinite(item.probability) && item.probability >= 0 && item.probability <= 1 &&
    Number.isSafeInteger(item.timestamp_ms) && item.timestamp_ms >= 0 &&
    typeof item.created_at === "string" && Number.isFinite(eventTime(item.created_at)) &&
    typeof item.ended_at === "string" && Number.isFinite(eventTime(item.ended_at)) &&
    Number.isSafeInteger(item.record_count) && item.record_count > 0 &&
    (item.reason === null || typeof item.reason === "string"));
  return { items, total: Number(data.total), page, page_size: 10 };
}

export async function clearAiReports(deviceId: string, signal?: AbortSignal): Promise<void> {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const url = new URL(`${base}/api/v1/reports/ai`);
  url.searchParams.set("device_id", deviceId);
  const send = () => fetch(url, { method: "DELETE", credentials: "include", signal });
  let response = await send();
  if (response.status === 401 && import.meta.env.DEV) {
    await openLocalSession(signal ?? new AbortController().signal);
    response = await send();
  }
  if (!response.ok) throw new Error("Không xóa được báo cáo.");
}


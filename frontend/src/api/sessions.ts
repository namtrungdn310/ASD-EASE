import { API_BASE_URL } from "./index";
import { openLocalSession } from "../utils/localSession";

export type SessionState = "STARTING" | "RECORDING" | "STOPPING" | "STOPPED" | "ABORTED" | "LEGACY";
export interface DeviceSession {
  session_id: string;
  device_id: string;
  data_origin: "DEVICE" | "SYNTHETIC";
  state: SessionState;
  requested_at: string | null;
  started_at: string | null;
  stopped_at: string | null;
  recording_complete: boolean;
  incomplete_reasons: string[];
}
const states = new Set(["STARTING", "RECORDING", "STOPPING", "STOPPED", "ABORTED", "LEGACY"]);
const identifier = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
const base = API_BASE_URL.replace(/\/$/, "");
const sessionsUrl = `${base.endsWith("/api/v1") ? base : `${base}/api/v1`}/sessions`;
export const isActiveSession = (session: DeviceSession | null) => session !== null &&
  (["STARTING", "RECORDING", "STOPPING"].includes(session.state) || (session.state === "LEGACY" && !session.stopped_at));

export class SessionApiError extends Error {
  constructor(readonly code: string) { super(code); }
}

export function parseDeviceSession(value: unknown): DeviceSession {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new SessionApiError("INVALID_RESPONSE");
  const row = value as Record<string, unknown>;
  if (typeof row.session_id !== "string" || !identifier.test(row.session_id) ||
      typeof row.device_id !== "string" || !identifier.test(row.device_id) ||
      !["DEVICE", "SYNTHETIC"].includes(String(row.data_origin)) || !states.has(String(row.state)) ||
      typeof row.recording_complete !== "boolean" || !Array.isArray(row.incomplete_reasons) ||
      !row.incomplete_reasons.every(reason => typeof reason === "string") ||
      !["requested_at", "started_at", "stopped_at"].every(key => row[key] === null ||
        (typeof row[key] === "string" && Number.isFinite(Date.parse(row[key] as string))))) {
    throw new SessionApiError("INVALID_RESPONSE");
  }
  return row as unknown as DeviceSession;
}

async function request(signal: AbortSignal): Promise<unknown> {
  const timeout = new AbortController();
  const abort = () => timeout.abort();
  signal.addEventListener("abort", abort, { once: true });
  if (signal.aborted) abort();
  const timer = window.setTimeout(abort, 8000);
  try {
    const send = () => fetch(sessionsUrl, {
      method: "GET", credentials: "include", cache: "no-store", signal: timeout.signal,
    });
    let response = await send();
    if (response.status === 401 && import.meta.env.DEV) {
      await openLocalSession(timeout.signal);
      response = await send();
    }
    const data = await response.json();
    if (!response.ok) throw new SessionApiError(typeof data?.detail === "string" ? data.detail : "REQUEST_REJECTED");
    if (timeout.signal.aborted) throw new SessionApiError("REQUEST_TIMEOUT");
    return data;
  } finally {
    window.clearTimeout(timer);
    signal.removeEventListener("abort", abort);
  }
}

export async function listDeviceSessions(signal: AbortSignal): Promise<DeviceSession[]> {
  const result = await request(signal);
  if (!Array.isArray(result)) throw new SessionApiError("INVALID_RESPONSE");
  return result.map(parseDeviceSession);
}

export function sessionErrorMessage(error: unknown): string {
  const code = error instanceof SessionApiError ? error.code : "NETWORK";
  const messages: Record<string, string> = {
    OPERATOR_AUTH_REQUIRED: "Phiên đăng nhập chưa sẵn sàng. Hãy thử lại.",
    INVALID_RESPONSE: "Chưa đọc được trạng thái phiên từ máy chủ.",
  };
  return messages[code] ?? "Chưa nhận được xác nhận. Đang kiểm tra lại trạng thái phiên.";
}

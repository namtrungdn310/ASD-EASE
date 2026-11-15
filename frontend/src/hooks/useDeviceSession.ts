import { useEffect, useState } from "react";
import { isActiveSession, listDeviceSessions, sessionErrorMessage } from "../api/sessions";
import type { DeviceSession } from "../api/sessions";
import type { DataOrigin } from "../types/telemetry";

/** Chỉ đọc trạng thái bền từ backend; việc tự mở phiên không phụ thuộc browser. */
export function useDeviceSession(deviceId: string | null, origin?: DataOrigin) {
  const [session, setSession] = useState<DeviceSession | null>(null);
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;
    const poll = async () => {
      let nextDelay = 4000;
      try {
        if (!deviceId || !origin) return;
        const rows = await listDeviceSessions(controller.signal);
        if (controller.signal.aborted) return;
        const matching = rows.filter(row => row.device_id === deviceId && row.data_origin === origin)
          .sort((a, b) => (Date.parse(b.requested_at ?? "") || 0) - (Date.parse(a.requested_at ?? "") || 0));
        const found = matching.find(isActiveSession) ?? matching[0] ?? null;
        setSession(found); setVerified(true); setError("");
        if (isActiveSession(found)) nextDelay = 1000;
      } catch (failure) {
        if (!controller.signal.aborted) { setVerified(false); setError(sessionErrorMessage(failure)); }
      } finally {
        if (!controller.signal.aborted && deviceId && origin) timer = window.setTimeout(poll, nextDelay);
      }
    };
    void poll();
    return () => { controller.abort(); if (timer !== undefined) window.clearTimeout(timer); };
  }, [deviceId, origin]);
  return { session, verified, error };
}

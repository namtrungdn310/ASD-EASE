import type { DataOrigin } from "../types/telemetry";
import { useDeviceSession } from "../hooks/useDeviceSession";

const labels = { STARTING: "Đang chờ ESP xác nhận phiên", RECORDING: "Phiên đang hoạt động",
  STOPPING: "Đang kết thúc phiên", STOPPED: "Phiên đã kết thúc", ABORTED: "Phiên bị gián đoạn", LEGACY: "Phiên cũ cần kiểm tra" };

function SelectedSessionControl({ deviceId, origin, live, telemetrySessionId }: {
  deviceId: string | null; origin?: DataOrigin; live: boolean; telemetrySessionId: string | null;
}) {
  const { session, verified, error } = useDeviceSession(deviceId, origin);
  const knownId = session?.session_id ?? telemetrySessionId;
  const displayId = knownId?.replace(/^AUTO-/i, "");
  const confirmedLive = live && telemetrySessionId !== null && (!session || session.session_id === telemetrySessionId) &&
    (!session || session.state === "RECORDING");
  const label = confirmedLive ? "Phiên đang hoạt động" : session ?
    session.state === "RECORDING" ? "Đang chờ dữ liệu trong phiên" : labels[session.state] :
    !deviceId ? "Chờ thiết bị" :
    !live ? "Chờ thiết bị kết nối" : verified ? "Đang mở phiên tự động" : "Đang kiểm tra phiên";
  if (!knownId) return null;

  return <div className="header-session" aria-label="Mã phiên" role="status" aria-atomic="true"
    data-state={confirmedLive ? "RECORDING" : session?.state}>
    <span className="header-session-value">{displayId}</span>
    <span className="sr-only"> · {label}</span>
    {error && <span className="sr-only"> · {error}</span>}
  </div>;
}
export function SessionControl(props: { deviceId: string | null; origin?: DataOrigin; live: boolean; telemetrySessionId: string | null }) {
  return <SelectedSessionControl key={`${props.origin ?? "none"}:${props.deviceId ?? "none"}`} {...props} />;
}

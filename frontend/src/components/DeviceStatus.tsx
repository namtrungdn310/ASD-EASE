import { Clock3, Radio, TriangleAlert, WifiOff } from "lucide-react";
import type { ConnectionStatus } from "../types/connection";

const states = {
  live: { label: "Đang cập nhật", description: "Đã nhận dữ liệu mới từ thiết bị.", icon: Radio },
  waiting: { label: "Chờ dữ liệu", description: "Kết nối đã sẵn sàng, đang chờ mẫu mới.", icon: Clock3 },
  stale: { label: "Dữ liệu cũ", description: "Chưa nhận mẫu mới trong hơn 5 giây.", icon: TriangleAlert },
  backend_disconnected: { label: "Chưa kết nối", description: "Chưa nhận dữ liệu mới từ thiết bị.", icon: WifiOff },
};
export function DeviceStatus({ status, deviceId, connected, connecting = false, inline = false }: {
  status?: ConnectionStatus; deviceId?: string; connected?: boolean; connecting?: boolean; inline?: boolean;
}) {
  const resolved = connecting ? "waiting" : status ?? (connected ? "live" : "backend_disconnected");
  const state = states[resolved];
  const Icon = state.icon;
  const visibleLabel = resolved === "live" ? "Đã kết nối" : connecting ? "Đang kết nối" : "Chưa kết nối";
  return <div className="connection-badge" data-status={resolved}
    data-device-connected={resolved === "live"}
    role="status" aria-live="polite" aria-atomic="true" title={state.description}>
    {!inline && <Icon size={15} aria-hidden="true" />}
    {!inline && <span className="device-status-label">Thiết bị:</span>}
    <span>{visibleLabel}{connecting && <> <span className="connection-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span></>}</span>
    <span className="sr-only">. {state.label}. {deviceId ?? "Chưa có thiết bị"}</span>
  </div>;
}

import {Radio, WifiOff} from "lucide-react";

export function DeviceStatus({connected, deviceId}: {connected: boolean; deviceId?: string}) {
  const Icon = connected ? Radio : WifiOff;
  return <section className="card flex items-center gap-3" aria-label="Trạng thái kết nối">
    <span className={`icon-shell ${connected ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}><Icon size={20} aria-hidden="true" /></span>
    <div><p className="eyebrow">Thiết bị</p><p className="font-semibold text-slate-900">{connected ? deviceId ?? "Đang chờ dữ liệu" : "Chưa kết nối"}</p></div>
    <span className={`ml-auto status-dot ${connected ? "bg-emerald-500" : "bg-slate-300"}`} aria-hidden="true" />
  </section>;
}


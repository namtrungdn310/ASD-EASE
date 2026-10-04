import {Activity, FlaskConical, Gauge, Waves} from "lucide-react";
import {DeviceStatus} from "../components/DeviceStatus";
import {StateCard} from "../components/StateCard";
import {SignalQuality} from "../components/SignalQuality";
import {HeartRateChart} from "../components/HeartRateChart";
import {GSRChart} from "../components/GSRChart";
import {MovementChart} from "../components/MovementChart";
import {ProbabilityChart} from "../components/ProbabilityChart";
import {useLiveTelemetry} from "../hooks/useLiveTelemetry";

const display = (value: number | null | undefined, suffix = "") => value == null ? "—" : `${value.toFixed(1)}${suffix}`;

export function Dashboard() {
  const {telemetry, points, connected} = useLiveTelemetry();
  return <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow text-teal-700">Local engineering monitor</p><h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">ASD Edge AI</h1><p className="mt-2 max-w-2xl text-sm text-slate-600">Dashboard hiển thị trạng thái kỹ thuật từ thiết bị. Không phải công cụ chẩn đoán y khoa.</p></div>
      {telemetry?.data_origin === "SYNTHETIC" && <div className="flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-bold text-violet-800"><FlaskConical size={17} aria-hidden="true" /> SYNTHETIC DATA</div>}
    </header>
    <div className="grid gap-4 md:grid-cols-3"><DeviceStatus connected={connected} deviceId={telemetry?.device_id} /><StateCard state={telemetry?.prediction.state} probability={telemetry?.prediction.probability} /><SignalQuality quality={telemetry?.signal_quality} /></div>
    <section className="my-4 grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Chỉ số hiện tại">
      {[[Activity, "HR", display(telemetry?.hr_bpm, " bpm")], [Waves, "GSR", display(telemetry?.gsr.raw, " ADC")], [Gauge, "Movement", display(telemetry?.movement.score)], [FlaskConical, "Session", telemetry?.session_id ?? "—"]].map(([Icon, label, value]) => { const MetricIcon = Icon as typeof Activity; return <div className="metric" key={label as string}><MetricIcon size={18} className="text-teal-700" aria-hidden="true" /><div><p className="eyebrow">{label as string}</p><p className="mt-0.5 font-mono font-semibold text-slate-900">{value as string}</p></div></div>; })}
    </section>
    <div className="grid gap-4 lg:grid-cols-2"><HeartRateChart data={points} /><GSRChart data={points} /><MovementChart data={points} /><ProbabilityChart data={points} /></div>
    <footer className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-t border-slate-200 pt-4 text-xs text-slate-500"><span>Firmware: {telemetry?.firmware_version ?? "—"}</span><span>Model: {telemetry?.model_version ?? "—"}</span><span>Schema: {telemetry?.schema_version ?? "1.0"}</span></footer>
  </main>;
}


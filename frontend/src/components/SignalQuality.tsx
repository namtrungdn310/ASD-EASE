import type {Telemetry} from "../types/telemetry";

export function SignalQuality({quality}: {quality?: Telemetry["signal_quality"]}) {
  return <section className="card"><p className="eyebrow">Chất lượng tín hiệu</p><div className="mt-3 space-y-3">{(["ppg", "gsr", "imu"] as const).map((key) => {
    const value = quality?.[key] ?? 0;
    return <div key={key}><div className="mb-1 flex justify-between text-xs font-semibold uppercase text-slate-600"><span>{key}</span><span>{Math.round(value * 100)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-600 transition-[width] duration-200 motion-reduce:transition-none" style={{width: `${value * 100}%`}} /></div></div>;
  })}</div></section>;
}


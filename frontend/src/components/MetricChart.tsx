import {CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis} from "recharts";
import type {ChartPoint} from "../types/telemetry";

export function MetricChart({title, data, dataKey, color, unit}: {title: string; data: ChartPoint[]; dataKey: keyof ChartPoint; color: string; unit: string}) {
  return <section className="card min-h-64"><div className="mb-4 flex items-baseline justify-between"><h2 className="font-semibold text-slate-900">{title}</h2><span className="text-xs text-slate-500">{unit}</span></div>
    {data.length === 0 ? <div className="grid h-44 place-items-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-500">Đang chờ luồng telemetry…</div> : <div className="h-44" role="img" aria-label={`Biểu đồ ${title}`}><ResponsiveContainer width="100%" height="100%"><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="time" tick={{fontSize: 11}} unit="s" /><YAxis width={44} tick={{fontSize: 11}} /><Tooltip formatter={(value) => [`${value ?? "—"} ${unit}`, title]} /><Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div>}
  </section>;
}


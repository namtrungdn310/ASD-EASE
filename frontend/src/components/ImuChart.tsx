import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useEffect, useId, useRef, useState } from "react";
import type { ChartPoint } from "../types/telemetry";
import { useChartAxis } from "../hooks/useChartAxis";
import { withChartGaps } from "../utils/chartWindow";
import { axisTicks } from "../utils/chartAxis";
import { axisStyle, timeAxisLayout, valueAxisLayout, chartTimeDomain, chartTimeTicks, formatChartNumber, formatChartTime, tooltipStyle } from "../utils/chartFormat";

const groups = {
  acceleration: { title: "Gia tốc", unit: "m/s²", keys: ["ax", "ay", "az"] as const },
  angular_velocity: { title: "Tốc độ xoay", unit: "°/s", keys: ["gx", "gy", "gz"] as const },
};
const colors = ["#0638d8", "#16705c", "#946134"];
const dashes = [undefined, "7 4", "2 3"];

function AccelerationStrip({ data, axis, index, syncId, height }: {
  data: ChartPoint[]; axis: "ax" | "ay" | "az"; index: number; syncId: string; height: number;
}) {
  const domain = useChartAxis(axis, data);
  const plotData = withChartGaps(data);
  const label = `A${axis[1]}`;
  const count = data.filter(point => point[axis] != null).length;
  const bottom = axis === "az";
  return <div className="imu-strip" role="group" aria-label={`Biểu đồ ${label}, đơn vị m/s², trục OY riêng`}>
    <div className="imu-strip-plot" style={{ height }}>
      <ResponsiveContainer width="100%" height={height} minWidth={0}><LineChart data={plotData} syncId={syncId}
        margin={{ top: 6, right: 8, bottom: 0, left: 0 }} accessibilityLayer>
        <CartesianGrid vertical={false} horizontalValues={[axisTicks(domain)[1]]} strokeDasharray="3 4" stroke="#e8edf4" />
        <XAxis {...axisStyle} {...timeAxisLayout} dataKey="time" type="number" domain={chartTimeDomain(data)} ticks={chartTimeTicks(data)}
          hide={!bottom} tickFormatter={formatChartTime} interval={0} height={bottom ? timeAxisLayout.height : 0} />
        <YAxis {...axisStyle} {...valueAxisLayout} domain={domain} ticks={[axisTicks(domain)[1]]} tickFormatter={formatChartNumber} />
        <Tooltip contentStyle={tooltipStyle} labelFormatter={value => `${formatChartTime(Number(value))} · Thang ${formatChartNumber(domain[0])} đến ${formatChartNumber(domain[1])} m/s²`}
          formatter={value => [`${value == null ? "—" : formatChartNumber(Number(value))} m/s²`, label]}
          cursor={{ stroke: "#cbd5e1", strokeDasharray: "3 3" }} />
        <Line type="linear" dataKey={axis} name={label} stroke={colors[index]} strokeDasharray={dashes[index]}
          strokeWidth={2} dot={count === 1 ? { r: 3, strokeWidth: 0 } : false}
          activeDot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
      </LineChart></ResponsiveContainer>
      {count === 0 && <span className="imu-strip-empty">Chưa có mẫu</span>}
    </div>
  </div>;
}

function AccelerationPlot({ data }: { data: ChartPoint[] }) {
  const syncId = useId();
  const container = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(216);
  const available = data.some(point => groups.acceleration.keys.some(key => point[key] != null));
  useEffect(() => {
    const element = container.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const resize = (value: number) => { if (value > 0) setHeight(Math.max(120, Math.floor(value))); };
    resize(element.getBoundingClientRect().height);
    const observer = new ResizeObserver(entries => resize(entries[0]?.contentRect.height ?? 0));
    observer.observe(element);
    return () => observer.disconnect();
  }, [available]);
  const lane = Math.max(24, Math.floor((height - 48) / 3));
  const bottom = height - 12 - 2 * lane;
  return !available ? <div className="plot-empty">Chưa có mẫu hợp lệ</div> :
    <div ref={container} className="imu-strips" style={{ gridTemplateRows: `${lane}px ${lane}px ${bottom}px`, gap: 6 }} role="group" aria-label="Biểu đồ Gia tốc, đơn vị m/s², ba trục OY riêng và chung thời gian">
      {groups.acceleration.keys.map((axis, index) =>
        <AccelerationStrip key={axis} data={data} axis={axis} index={index} syncId={syncId} height={index === 2 ? bottom : lane} />)}
    </div>;
}

function RotationPlot({ data, embedded }: { data: ChartPoint[]; embedded: boolean }) {
  const { title, unit, keys } = groups.angular_velocity;
  const domain = useChartAxis("angular_velocity", data);
  const plotData = withChartGaps(data);
  const available = data.some(point => keys.some(key => point[key] != null));
  const plot = !available ? <div className="plot-empty">Chưa có mẫu hợp lệ</div> :
    <div className="plot-area" role="group" aria-label={`Biểu đồ ${title}, đơn vị ${unit}`}>
      <ResponsiveContainer width="100%" height="100%"><LineChart data={plotData} margin={{ top: 10, right: 8, bottom: 0, left: 0 }} accessibilityLayer>
        <CartesianGrid vertical={false} strokeDasharray="3 4" stroke="#e8edf4" />
        <XAxis {...axisStyle} {...timeAxisLayout} dataKey="time" type="number" domain={chartTimeDomain(data)} ticks={chartTimeTicks(data)}
          tickFormatter={formatChartTime} interval={0} />
        <YAxis {...axisStyle} {...valueAxisLayout} domain={domain} ticks={axisTicks(domain)} tickFormatter={formatChartNumber} />
        <Tooltip contentStyle={tooltipStyle} labelFormatter={value => formatChartTime(Number(value))}
          formatter={(value, name) => [`${value == null ? "—" : formatChartNumber(Number(value))} ${unit}`, name]}
          cursor={{ stroke: "#cbd5e1", strokeDasharray: "3 3" }} />
        {!embedded && <Legend iconType="plainline" iconSize={18} wrapperStyle={{ fontSize: "var(--type-caption-size)", paddingTop: 6 }} />}
        {keys.map((key, index) => <Line key={key} type="linear" dataKey={key}
          name={`${key[0].toUpperCase()}${key[1]}`} stroke={colors[index]} strokeDasharray={dashes[index]}
          strokeWidth={2} dot={data.filter(point => point[key] != null).length === 1 ? { r: 3, strokeWidth: 0 } : false}
          activeDot={{ r: 4, stroke: "white", strokeWidth: 2 }} connectNulls={false} isAnimationActive={false} />)}
      </LineChart></ResponsiveContainer>
    </div>;
  return plot;
}

export function ImuChart({ data, kind, embedded = false }: { data: ChartPoint[]; kind: keyof typeof groups; embedded?: boolean }) {
  const plot = kind === "acceleration" ? <AccelerationPlot data={data} /> : <RotationPlot data={data} embedded={embedded} />;
  return embedded ? plot : <section className="analysis-chart"><h3>{groups[kind].title}</h3>{plot}</section>;
}

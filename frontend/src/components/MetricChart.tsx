import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartPoint } from "../types/telemetry";
import { useChartAxis } from "../hooks/useChartAxis";
import { withChartGaps } from "../utils/chartWindow";
import { axisTicks } from "../utils/chartAxis";
import { axisStyle, timeAxisLayout, valueAxisLayout, chartTimeDomain, chartTimeTicks, formatChartNumber, formatChartTime, tooltipStyle } from "../utils/chartFormat";

type MetricChartPoint = ChartPoint & { hrForecast?: number | null };

export function MetricChart({ title, data, dataKey, color, unit, embedded = false, forecast }: {
  title: string; data: MetricChartPoint[]; dataKey: keyof ChartPoint; color: string; unit: string; embedded?: boolean;
  forecast?: { dataKey: "hrForecast"; name: string; color: string };
}) {
  const kind = dataKey === "hr" || dataKey === "gsr" || dataKey === "probability" ? dataKey : "movement";
  const domain = useChartAxis(kind, data);
  const plotData = withChartGaps(data);
  const validPoints = data.filter(point => point[dataKey] != null).length;
  const forecastPoints = forecast ? data.filter(point => point[forecast.dataKey] != null).length : 0;
  const hasData = validPoints > 0 || forecastPoints > 0;
  const plot = !hasData ? <div className="plot-empty">Chưa có mẫu hợp lệ</div> :
    <div className="plot-area" role="group" aria-label={`Biểu đồ ${title}, đơn vị ${unit}`}>
      <ResponsiveContainer width="100%" height="100%"><LineChart data={plotData} margin={{ top: 10, right: 8, bottom: 0, left: 0 }} accessibilityLayer>
        <CartesianGrid vertical={false} stroke="#e8edf4" strokeDasharray="3 4" />
        <XAxis {...axisStyle} {...timeAxisLayout} dataKey="time" type="number" domain={chartTimeDomain(data)} ticks={chartTimeTicks(data)}
          tickFormatter={formatChartTime} interval={0} />
        <YAxis {...axisStyle} {...valueAxisLayout} domain={domain} ticks={axisTicks(domain, dataKey === "gsr")} tickFormatter={formatChartNumber} allowDecimals={dataKey !== "gsr"} />
        <Tooltip contentStyle={tooltipStyle} labelFormatter={value => formatChartTime(Number(value))}
          formatter={(value, name) => [`${value == null ? "—" : formatChartNumber(Number(value))} ${unit}`, forecast && name === forecast.name ? forecast.name : title]}
          cursor={{ stroke: "#cbd5e1", strokeDasharray: "3 3" }} />
        <Line type="linear" dataKey={dataKey} name={title} stroke={color} strokeWidth={2}
          dot={validPoints === 1 ? { r: 3, strokeWidth: 0 } : false} activeDot={{ r: 4, strokeWidth: 2, stroke: "white" }} connectNulls={false} isAnimationActive={false} />
        {forecast && <Line type="linear" dataKey={forecast.dataKey} name={forecast.name} stroke={forecast.color}
          strokeWidth={2} strokeDasharray="5 4" dot={false} activeDot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />}
      </LineChart></ResponsiveContainer>
    </div>;
  return embedded ? plot : <section className="analysis-chart"><h3>{title}</h3>{plot}</section>;
}


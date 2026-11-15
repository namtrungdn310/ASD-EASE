import type { ChartPoint } from "../types/telemetry";
import { CHART_WINDOW_SECONDS } from "./chartWindow";

/** Thời gian trên thiết bị, không phải giờ nhận gói ở laptop. */
export function formatChartTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const whole = Math.floor(seconds);
  return `${Math.floor(whole / 60).toString().padStart(2, "0")}:${(whole % 60).toString().padStart(2, "0")}`;
}
export function formatChartNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)));
}
export function chartTimeDomain(data: ChartPoint[]): [number, number] {
  const last = data.at(-1)?.time ?? 0;
  const end = Math.max(CHART_WINDOW_SECONDS, last);
  return [end - CHART_WINDOW_SECONDS, end];
}
export function chartTimeTicks(data: ChartPoint[]): number[] {
  const [start, end] = chartTimeDomain(data);
  const intervals = 4;
  return Array.from({ length: intervals + 1 }, (_, i) => start + (end - start) * i / intervals);
}
export const axisStyle = {
  tick: { fontSize: "var(--type-caption-size)", fill: "var(--muted)", fontFamily: "inherit", fontWeight: 400 },
  axisLine: false, tickLine: false,
};
// Cùng khoảng cách nhãn cho mọi biểu đồ; tránh OX sát mốc cuối OY ở góc trái.
export const timeAxisLayout = { height: 36, tickMargin: 16, padding: { left: 12, right: 8 } };
export const valueAxisLayout = { width: 56, tickMargin: 8, interval: 0 as const };
export const tooltipStyle = {
  border: "1px solid #dce3ed", borderRadius: 8, fontSize: "var(--type-body-size)", fontWeight: 400, lineHeight: "var(--type-leading-body)",
  boxShadow: "0 4px 16px #10213d10", padding: "10px 12px",
};

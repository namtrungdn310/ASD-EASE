import type { ChartPoint } from "../types/telemetry";
import { MetricChart } from "./MetricChart";
export const GSRChart = ({data, embedded = false}: {data: ChartPoint[]; embedded?: boolean}) =>
  <MetricChart title="Điện da" data={data} dataKey="gsr" color="#16705c" unit="ADC" embedded={embedded} />;


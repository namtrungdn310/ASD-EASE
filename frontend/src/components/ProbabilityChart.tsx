import type {ChartPoint} from "../types/telemetry"; import {MetricChart} from "./MetricChart";
export const ProbabilityChart = ({data}: {data: ChartPoint[]}) => <MetricChart title="Xác suất mô phỏng" data={data} dataKey="probability" color="#c2410c" unit="0–1" />;


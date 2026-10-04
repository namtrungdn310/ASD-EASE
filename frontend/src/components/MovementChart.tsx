import type {ChartPoint} from "../types/telemetry"; import {MetricChart} from "./MetricChart";
export const MovementChart = ({data}: {data: ChartPoint[]}) => <MetricChart title="Điểm chuyển động" data={data} dataKey="movement" color="#2563eb" unit="0–1" />;


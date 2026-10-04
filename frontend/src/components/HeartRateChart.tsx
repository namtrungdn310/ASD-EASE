import type {ChartPoint} from "../types/telemetry"; import {MetricChart} from "./MetricChart";
export const HeartRateChart = ({data}: {data: ChartPoint[]}) => <MetricChart title="Nhịp tim ước tính" data={data} dataKey="hr" color="#e11d48" unit="bpm" />;


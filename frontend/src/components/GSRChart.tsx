import type {ChartPoint} from "../types/telemetry"; import {MetricChart} from "./MetricChart";
export const GSRChart = ({data}: {data: ChartPoint[]}) => <MetricChart title="GSR thô" data={data} dataKey="gsr" color="#0f766e" unit="ADC" />;


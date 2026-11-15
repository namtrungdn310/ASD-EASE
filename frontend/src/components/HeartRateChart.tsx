import type { ChartPoint } from "../types/telemetry";
import { MetricChart } from "./MetricChart";
import { heartRatePlot } from "../utils/heartRateDisplay";
export const HeartRateChart = ({data, embedded = false, tracked = false}: {data: ChartPoint[]; embedded?: boolean; tracked?: boolean}) => <>
  <MetricChart title="Nhịp tim" data={heartRatePlot(data, tracked)} dataKey="hr" color="#0638d8" unit="bpm" embedded={embedded}
    forecast={tracked ? { dataKey: "hrForecast", name: "Tạm tính", color: "#a16207" } : undefined} />
  {tracked && !embedded && <p className="chart-caption">Nét đứt: tạm tính tối đa 15 giây.</p>}
</>;


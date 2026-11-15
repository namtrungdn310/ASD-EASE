import { useState } from "react";
import { advanceAxis, observeAxis } from "../utils/chartAxis";
import type { AxisKind } from "../utils/chartAxis";
import type { ChartPoint } from "../types/telemetry";

/** Lưu lịch sử thang đo, không sửa history/telemetry và không dùng timer nền. */
export function useChartAxis(kind: AxisKind, data: readonly (ChartPoint & { hrForecast?: number | null })[]) {
  const observation = observeAxis(kind, data);
  // So giá trị thay vì tham chiếu mảng: heartRatePlot có thể tạo mảng mới mỗi render.
  const signature = `${kind}:${observation.frameTime}:${observation.sampleTime}:${observation.min}:${observation.max}`;
  const [saved, setSaved] = useState(() => ({ signature, axis: advanceAxis(null, kind, observation) }));
  if (saved.signature !== signature) {
    const axis = advanceAxis(saved.axis, kind, observation);
    setSaved({ signature, axis });
    return axis.domain;
  }
  return saved.axis.domain;
}

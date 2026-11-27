import type { ChartPoint, Telemetry } from "../types/telemetry";

export const HR_FORECAST_SECONDS = 15;

// Dự báo ngắn trên lớp trình bày, KHÔNG ghi vào hr/telemetry/DB.
// Có thể dùng dự báo hằng khi chưa đủ lịch sử để ước lượng xu hướng.
export function forecastHeartRate(history: readonly ChartPoint[], now: number) {
  if (!history.length || !Number.isFinite(now)) return null;
  if (history.some((point, i) => !Number.isFinite(point.time) ||
    (i > 0 && point.time <= history[i - 1].time))) return null;
  const measured = history.filter(point => point.hr !== null && Number.isFinite(point.hr));
  const last = measured[measured.length - 1];
  if (!last || last.hr === null || last.time > now || history[history.length - 1].time > now) return null;
  if (history.some(point => point.time >= last.time && point.time <= now && point.hrNoContact)) return null;
  const age = now - last.time;
  if (age <= 0 || age > HR_FORECAST_SECONDS) return null;
  const recent = measured.filter(point => point.time >= last.time - 8).slice(-3);
  let slope = 0;
  if (recent.length === 3) {
    const [a, b, c] = recent;
    const first = b.hr! - a.hr!;
    const second = c.hr! - b.hr!;
    if (first * second >= 0 && c.time - a.time >= 1) {
      slope = Math.max(-1, Math.min(1, (c.hr! - a.hr!) / (c.time - a.time)));
    }
  }
  // Xu hướng tắt dần, tổng dịch chuyển tối đa3bpm; không ép về dải nhịp nghỉ.
  const value = last.hr + slope * 3 * (1 - Math.exp(-age / 3));
  if (!Number.isFinite(value) || value < 20 || value > 240) return null;
  return { value, ageSeconds: Math.max(1, Math.ceil(age)) };
}

export type HeartRatePlotPoint = ChartPoint & { hrForecast: number | null };

export function heartRatePlot(points: readonly ChartPoint[], enabled: boolean): HeartRatePlotPoint[] {
  const result = points.map(point => ({ ...point, hrForecast: null as number | null }));
  if (!enabled) return result;
  for (let i = 0; i < result.length; i++) {
    const point = result[i];
    if (point.hr !== null) {
      if (i > 0 && points[i - 1].hr === null && result[i - 1].hrForecast !== null) point.hrForecast = point.hr;
      continue;
    }
    const prediction = forecastHeartRate(points.slice(0, i + 1), point.time);
    if (!prediction) continue;
    point.hrForecast = prediction.value;
    if (i > 0 && points[i - 1].hr !== null) result[i - 1].hrForecast = points[i - 1].hr;
  }
  return result;
}

// points do useLiveTelemetry tách theo thiết bị/phiên/nguồn trước khi gọi.
export function heartRateDisplay(telemetry: Telemetry | null, points: readonly ChartPoint[], live: boolean) {
  const tracked = telemetry?.firmware_version.endsWith("-tracker") ?? false;
  const estimated = tracked || (telemetry?.firmware_version.endsWith("-demo") ?? false);
  const value = telemetry?.hr_bpm ?? null;
  const noContact = telemetry?.schema_version === "1.2" && telemetry.signal_quality.hr.reason === "no_contact";
  const fresh = { value, estimated, tracked, held: false, predicted: false, ageSeconds: null as number | null };
  if (!telemetry || value !== null || !estimated || !live || noContact) return fresh;
  const now = telemetry.timestamp_ms / 1000;
  // Clock lùi/đổi boot: không lấy một số ở "tương lai" làm nhịp hiện tại.
  if (points.length && points[points.length - 1].time > now) return fresh;
  if (tracked) {
    const prediction = forecastHeartRate(points, now);
    return prediction ? { ...fresh, ...prediction, predicted: true } : fresh;
  }
  for (let i = points.length - 1; i >= 0; i--) {
    const point = points[i];
    if (point.hr === null) continue;
    const elapsed = now - point.time;
    if (elapsed < 0 || elapsed > 10) return fresh;
    return { value: point.hr, estimated, tracked, held: true, predicted: false, ageSeconds: Math.max(1, Math.ceil(elapsed)) };
  }
  return fresh;
}

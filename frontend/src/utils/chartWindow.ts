// Cửa sổ theo thời gian thiết bị, độc lập số gói nhận được.
export const CHART_WINDOW_SECONDS = 60;
export const CHART_GAP_SECONDS = 1.8;

/** Chèn điểm ngắt chỉ để vẽ, không thêm mẫu vào lịch sử/DB. */
export function withChartGaps<T extends { time: number }>(points: readonly T[]): T[] {
  const result: T[] = [];
  for (const point of points) {
    const previous = result.at(-1);
    if (previous && point.time - previous.time > CHART_GAP_SECONDS) {
      const gap = Object.fromEntries(Object.keys(point).map(key => [key, key === "time" ? (previous.time + point.time) / 2 : null]));
      result.push(gap as T);
    }
    result.push(point);
  }
  return result;
}

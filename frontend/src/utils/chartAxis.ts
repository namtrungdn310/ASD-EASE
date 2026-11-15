/** Thang hiển thị kỹ thuật; không phải ngưỡng sức khỏe hoặc phép lọc số đo. */
export type AxisKind = "hr" | "gsr" | "ax" | "ay" | "az" | "angular_velocity" | "probability" | "movement";
export type AxisDomain = [number, number];
export type AxisField = "hr" | "hrForecast" | "gsr" | "ax" | "ay" | "az" | "gx" | "gy" | "gz" | "probability" | "movement";
type AxisPoint = { time: number } & Partial<Record<AxisField, number | null>>;
export interface AxisObservation {
  min: number | null;
  max: number | null;
  sampleTime: number | null;
  frameTime: number | null;
}
export interface AxisState {
  kind: AxisKind;
  domain: AxisDomain;
  sampleTime: number | null;
  frameTime: number | null;
  pending: { since: number; domain: AxisDomain } | null;
}
export const AXIS_SHRINK_DELAY_SECONDS = 15;
const keys: Record<AxisKind, readonly AxisField[]> = {
  hr: ["hr", "hrForecast"], gsr: ["gsr"], ax: ["ax"], ay: ["ay"], az: ["az"],
  angular_velocity: ["gx", "gy", "gz"], probability: ["probability"], movement: ["movement"],
};
export function observeAxis(kind: AxisKind, data: readonly AxisPoint[]): AxisObservation {
  let min = Infinity, max = -Infinity, sampleTime: number | null = null;
  for (const point of data) {
    if (!Number.isFinite(point.time)) continue;
    for (const key of keys[kind]) {
      const value = point[key];
      if (value == null || !Number.isFinite(value)) continue;
      min = Math.min(min, value); max = Math.max(max, value);
      sampleTime = point.time;
    }
  }
  const last = data.at(-1)?.time;
  return { min: min === Infinity ? null : min, max: max === -Infinity ? null : max,
    sampleTime, frameTime: last != null && Number.isFinite(last) ? last : null };
}
const union = (a: AxisDomain, b: AxisDomain): AxisDomain => [Math.min(a[0], b[0]), Math.max(a[1], b[1])];
const same = (a: AxisDomain, b: AxisDomain) => a[0] === b[0] && a[1] === b[1];
function niceCeil(value: number) {
  const power = 10 ** Math.floor(Math.log10(value));
  return [1, 2, 5, 10].find(step => value <= step * power)! * power;
}
export function requestedAxisDomain(kind: AxisKind, observation: AxisObservation): AxisDomain {
  const { min, max } = observation;
  if (kind === "probability" || kind === "movement") return [0, 1];
  if (kind === "angular_velocity") {
    const base = .2;
    const peak = Math.max(Math.abs(min ?? 0), Math.abs(max ?? 0));
    const limit = peak <= base ? base : niceCeil(peak * 1.1);
    return [-limit, limit];
  }
  if (min == null || max == null)
    return kind === "hr" ? [40, 160] : kind === "gsr" ? [0, 4095] : [-.1, .1];
  // Miền quanh dữ liệu thật, có sàn độ rộng để tránh phóng quá sát nhiễu nhỏ.
  const minimumSpan = kind === "hr" ? 30 : kind === "gsr" ? 100 : .2;
  const step = kind === "hr" ? 5 : kind === "gsr" ? 20 : .05;
  const padding = Math.max(0, (minimumSpan - (max - min)) / 2, (max - min) * .15);
  let low = Math.floor((min - padding) / step + 1e-9) * step;
  let high = Math.ceil((max + padding) / step - 1e-9) * step;
  if ((kind === "hr" || kind === "gsr") && low < 0) { high -= low; low = 0; }
  if (kind === "gsr" && high > 4095) { low = Math.max(0, low - (high - 4095)); high = 4095; }
  low = Number(low.toFixed(6)); high = Number(high.toFixed(6));
  // Không cắt một giá trị ngoài dự kiến; backend vẫn chịu trách nhiệm kiểm schema.
  return [Math.min(low, min), Math.max(high, max)];
}
export function advanceAxis(previous: AxisState | null, kind: AxisKind, o: AxisObservation): AxisState {
  const wanted = requestedAxisDomain(kind, o);
  const reset = previous === null || previous.kind !== kind || previous.sampleTime === null || o.frameTime === null ||
    (previous.frameTime !== null && o.frameTime < previous.frameTime);
  if (reset) return { kind, domain: wanted, sampleTime: o.sampleTime, frameTime: o.frameTime, pending: null };
  const expanded = union(previous.domain, wanted);
  if (!same(expanded, previous.domain))
    return { kind, domain: expanded, sampleTime: o.sampleTime, frameTime: o.frameTime, pending: null };
  // Chỉ mẫu mới liên tục mới tích lũy thời gian thu hẹp; render lại/null/mất mạng không tính.
  const fresh = o.sampleTime !== null && (previous.sampleTime === null || o.sampleTime > previous.sampleTime);
  const gap = o.sampleTime === null || previous.sampleTime === null || o.sampleTime - previous.sampleTime > 5;
  let pending = gap || o.sampleTime !== o.frameTime ? null : previous.pending;
  const width = (domain: AxisDomain) => domain[1] - domain[0];
  if (same(wanted, previous.domain) || width(wanted) > width(previous.domain) * .9) pending = null;
  else if (fresh && o.sampleTime === o.frameTime) {
    const candidate = pending ? union(pending.domain, wanted) : wanted;
    if (width(candidate) > width(previous.domain) * .9) pending = { since: o.sampleTime!, domain: wanted };
    else if (pending && o.sampleTime! - pending.since >= AXIS_SHRINK_DELAY_SECONDS)
      return { kind, domain: candidate, sampleTime: o.sampleTime, frameTime: o.frameTime, pending: null };
    else pending = { since: pending?.since ?? o.sampleTime!, domain: candidate };
  }
  return { kind, domain: previous.domain, sampleTime: o.sampleTime, frameTime: o.frameTime, pending };
}
export function axisTicks(domain: AxisDomain, integer = false): number[] {
  const middle = (domain[0] + domain[1]) / 2;
  return [domain[0], integer ? Math.round(middle) : middle, domain[1]];
}

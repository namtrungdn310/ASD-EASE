export function isRecord(
  value: unknown
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

export function isFiniteNumber(
  value: unknown
): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function isNumberInRange(
  value: unknown,
  min: number,
  max: number
): value is number {
  return isFiniteNumber(value) && value >= min && value <= max;
}
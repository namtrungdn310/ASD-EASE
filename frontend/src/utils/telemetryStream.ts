import type { ConnectionStatus } from "../types/connection";
import type { ChartPoint, Telemetry } from "../types/telemetry";

export interface TelemetryStream {
  telemetry: Telemetry;
  points: ChartPoint[];
  receivedAtMs: number;
}

const MAX_CHART_POINTS = 60;

export function updateTelemetryStream(
  previous: TelemetryStream | null,
  next: Telemetry,
  receivedAtMs: number
): TelemetryStream {
  const sameStream =
    previous !== null &&
    previous.telemetry.device_id === next.device_id &&
    previous.telemetry.session_id === next.session_id &&
    previous.telemetry.data_origin === next.data_origin;

  if (
    previous !== null &&
    sameStream &&
    next.timestamp_ms === previous.telemetry.timestamp_ms
  ) {
    return previous;
  }

  const history =
    previous !== null &&
    sameStream &&
    next.timestamp_ms > previous.telemetry.timestamp_ms
      ? previous.points
      : [];

  const point: ChartPoint = {
    time: next.timestamp_ms / 1000,
    hr: next.hr_bpm,
    gsr: next.gsr.raw,
    movement: next.movement.score,
    probability: next.prediction.probability,
  };

  return {
    telemetry: next,
    points: [
      ...history.slice(-(MAX_CHART_POINTS - 1)),
      point,
    ],
    receivedAtMs,
  };
}

export function getConnectionStatus(
  backendConnected: boolean,
  stream: TelemetryStream | null,
  nowMs: number,
  staleTimeoutMs: number = 5000
): ConnectionStatus {
  if (!backendConnected) {
    return "backend_disconnected";
  }

  if (stream === null) {
    return "waiting";
  }

  if (nowMs - stream.receivedAtMs >= staleTimeoutMs) {
    return "stale";
  }

  return "live";
}
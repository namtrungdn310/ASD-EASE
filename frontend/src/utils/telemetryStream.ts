import type { ConnectionStatus } from "../types/connection";
import type { ChartPoint, Telemetry } from "../types/telemetry";
import { CHART_WINDOW_SECONDS } from "./chartWindow";

export interface TelemetryStream {
  telemetry: Telemetry;
  points: ChartPoint[];
  receivedAtMs: number;
  firstTimestampMs: number;
}

export function updateTelemetryStream(
  previous: TelemetryStream | null,
  next: Telemetry,
  receivedAtMs: number
): TelemetryStream {
  const sameStream =
    previous !== null &&
    previous.telemetry.device_id === next.device_id &&
    previous.telemetry.session_id === next.session_id &&
    previous.telemetry.data_origin === next.data_origin &&
    previous.telemetry.schema_version === next.schema_version;

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
    ax: next.schema_version !== "1.0" ? next.movement.acceleration?.x ?? null : null,
    ay: next.schema_version !== "1.0" ? next.movement.acceleration?.y ?? null : null,
    az: next.schema_version !== "1.0" ? next.movement.acceleration?.z ?? null : null,
    gx: next.schema_version !== "1.0" ? next.movement.angular_velocity?.x ?? null : null,
    gy: next.schema_version !== "1.0" ? next.movement.angular_velocity?.y ?? null : null,
    gz: next.schema_version !== "1.0" ? next.movement.angular_velocity?.z ?? null : null,
    probability: next.prediction.probability,
  };

  return {
    telemetry: next,
    points: [
      ...history.filter(point => point.time >= next.timestamp_ms / 1000 - CHART_WINDOW_SECONDS),
      point,
    ],
    receivedAtMs,
    firstTimestampMs: history.length && previous ? previous.firstTimestampMs : next.timestamp_ms,
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

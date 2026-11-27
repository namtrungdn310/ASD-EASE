import type { ConnectionStatus } from "../types/connection";
import type { ChartPoint, EngineeringState, Telemetry } from "../types/telemetry";
import { CHART_WINDOW_SECONDS } from "./chartWindow";

export interface TelemetryStream {
  telemetry: Telemetry;
  points: ChartPoint[];
  receivedAtMs: number;
  firstTimestampMs: number;
  awaitingResetCalibration?: number;
}

export function resetStreamAiWindow(stream: TelemetryStream): TelemetryStream {
  const isUncertain = stream.telemetry.prediction.state === "UNCERTAIN";
  const nextState: EngineeringState = isUncertain ? "UNCERTAIN" : "CALIBRATING";
  const resetPoints: ChartPoint[] = stream.points.map((point, index) => {
    const cleaned: ChartPoint = {
      ...point,
      probability: null,
      predictionState: undefined,
      calibValidSeconds: undefined,
      noContactSeconds: undefined,
    };
    if (index === stream.points.length - 1) {
      cleaned.predictionState = nextState;
      if (!isUncertain) cleaned.calibValidSeconds = 0;
    }
    return cleaned;
  });

  return {
    ...stream,
    telemetry: {
      ...stream.telemetry,
      prediction: {
        probability: null,
        state: nextState,
      },
    },
    points: resetPoints,
    ...(isUncertain ? {} : { awaitingResetCalibration: 3 }),
  };
}

export function updateTelemetryStream(
  previous: TelemetryStream | null,
  rawNext: Telemetry,
  receivedAtMs: number
): TelemetryStream {
  const sameStream =
    previous !== null &&
    previous.telemetry.device_id === rawNext.device_id &&
    previous.telemetry.session_id === rawNext.session_id &&
    previous.telemetry.data_origin === rawNext.data_origin &&
    previous.telemetry.schema_version === rawNext.schema_version;

  if (
    previous !== null &&
    sameStream &&
    rawNext.timestamp_ms === previous.telemetry.timestamp_ms
  ) {
    return previous;
  }

  let awaitingResetCalibration = sameStream ? previous?.awaitingResetCalibration : undefined;
  let holdingPreReset = false;
  let next = rawNext;
  if (awaitingResetCalibration && awaitingResetCalibration > 0) {
    if (rawNext.prediction.state === "CALIBRATING") {
      awaitingResetCalibration = undefined;
    } else if (rawNext.prediction.state === "NORMAL" || rawNext.prediction.state === "ATTENTION") {
      awaitingResetCalibration = awaitingResetCalibration > 1 ? awaitingResetCalibration - 1 : undefined;
      holdingPreReset = true;
      next = {
        ...rawNext,
        prediction: { probability: null, state: "CALIBRATING" },
      };
    } else {
      awaitingResetCalibration = undefined;
    }
  }

  const history =
    previous !== null &&
    sameStream &&
    next.timestamp_ms > previous.telemetry.timestamp_ms
      ? previous.points
      : [];

  const isNoContact = next.schema_version === "1.2" && next.signal_quality.hr.reason === "no_contact";
  const hasActiveModel = next.model_version !== "none" || next.data_origin === "SYNTHETIC";
  const prevLast = history.length > 0 ? history[history.length - 1] : undefined;
  let calibValidSeconds: number | undefined;
  let noContactSeconds: number | undefined;

  if (hasActiveModel) {
    if (next.prediction.state === "CALIBRATING") {
      // Kiểm tra xem vừa mới chuyển từ NORMAL / ATTENTION sang trong vòng 5 giây ân hạn hay không
      let dropLen = 0;
      let firstDropTimeSec: number | undefined;
      let priorActiveState: EngineeringState | undefined;
      for (let i = history.length - 1; i >= 0; i--) {
        const p = history[i];
        if (p.calibValidSeconds !== undefined || p.predictionState === "UNCERTAIN") break;
        if (p.predictionState === "CALIBRATING" || p.hrNoContact) {
          dropLen++;
          firstDropTimeSec = p.time;
        } else {
          priorActiveState = p.predictionState;
          break;
        }
      }
      const wasActiveOrInGrace =
        priorActiveState === "NORMAL" ||
        priorActiveState === "ATTENTION" ||
        (dropLen === 0 && (prevLast?.predictionState === "NORMAL" || prevLast?.predictionState === "ATTENTION"));

      if (wasActiveOrInGrace) {
        const nextTimeSec = next.timestamp_ms / 1000;
        const startSec = firstDropTimeSec ?? nextTimeSec;
        const graceCount = Math.max(dropLen + 1, Math.floor(nextTimeSec - startSec) + 1);
        if (graceCount <= 5) {
          noContactSeconds = graceCount;
        } else {
          calibValidSeconds = 1;
          noContactSeconds = 0;
        }
      } else {
        const prevWasCalib = prevLast?.predictionState === "CALIBRATING";
        const prevValid = prevWasCalib ? (prevLast?.calibValidSeconds ?? 0) : 0;
        const prevNoContact = prevWasCalib ? (prevLast?.noContactSeconds ?? 0) : 0;
        if (holdingPreReset) {
          calibValidSeconds = 0;
          noContactSeconds = 0;
        } else if (isNoContact) {
          calibValidSeconds = Math.max(1, prevValid);
          noContactSeconds = prevNoContact + 1;
        } else {
          calibValidSeconds = prevValid >= 60 ? 60 : prevValid + 1;
          noContactSeconds = 0;
        }
      }
    } else if ((next.prediction.state === "NORMAL" || next.prediction.state === "ATTENTION") && isNoContact) {
      noContactSeconds = (prevLast?.noContactSeconds ?? 0) + 1;
    }
  }

  const point: ChartPoint = {
    time: next.timestamp_ms / 1000,
    hr: next.hr_bpm,
    ...(isNoContact ? { hrNoContact: true } : {}),
    gsr: next.gsr.raw,
    movement: next.movement.score,
    ax: next.schema_version !== "1.0" ? next.movement.acceleration?.x ?? null : null,
    ay: next.schema_version !== "1.0" ? next.movement.acceleration?.y ?? null : null,
    az: next.schema_version !== "1.0" ? next.movement.acceleration?.z ?? null : null,
    gx: next.schema_version !== "1.0" ? next.movement.angular_velocity?.x ?? null : null,
    gy: next.schema_version !== "1.0" ? next.movement.angular_velocity?.y ?? null : null,
    gz: next.schema_version !== "1.0" ? next.movement.angular_velocity?.z ?? null : null,
    probability: next.prediction.probability,
    ...(hasActiveModel ? { predictionState: next.prediction.state } : {}),
    ...(calibValidSeconds !== undefined ? { calibValidSeconds } : {}),
    ...(noContactSeconds !== undefined && noContactSeconds > 0 ? { noContactSeconds } : {}),
  };

  return {
    telemetry: next,
    points: [
      ...history.filter(point => point.time >= next.timestamp_ms / 1000 - CHART_WINDOW_SECONDS),
      point,
    ],
    receivedAtMs,
    firstTimestampMs: history.length && previous ? previous.firstTimestampMs : next.timestamp_ms,
    ...(awaitingResetCalibration !== undefined ? { awaitingResetCalibration } : {}),
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

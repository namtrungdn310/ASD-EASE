import { useEffect, useState } from "react";
import { BrainCircuit, RotateCcw } from "lucide-react";
import type { ChartPoint, EngineeringState, Telemetry } from "../types/telemetry";
import { formatChartTime } from "../utils/chartFormat";
import { StateCard } from "./StateCard";
import { PanelTitle } from "./PanelTitle";

function pointPredictionState(point: ChartPoint): EngineeringState | undefined {
  if (point.predictionState) return point.predictionState;
  if (point.probability != null) return point.probability >= 0.7 ? "ATTENTION" : "NORMAL";
  return undefined;
}

function activePredictionPeriod(telemetry: Telemetry | null, points: ChartPoint[] | undefined, live: boolean, activeModel: boolean, effectiveState?: EngineeringState): string | null {
  const state = effectiveState ?? telemetry?.prediction.state;
  if (!live || !activeModel || (state !== "NORMAL" && state !== "ATTENTION") || !points || points.length < 2) {
    return null;
  }
  let startIdx = points.length - 1;
  while (startIdx > 0 && (points[startIdx].hrNoContact || (points[startIdx].calibValidSeconds === undefined && points[startIdx].predictionState !== state))) {
    startIdx--;
  }
  if (pointPredictionState(points[startIdx]) !== state) return null;
  while (startIdx > 0 && pointPredictionState(points[startIdx - 1]) === state) {
    startIdx--;
  }
  const startTime = points[startIdx].time;
  const endTime = points[points.length - 1].time;
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || endTime <= startTime) {
    return null;
  }
  return `${formatChartTime(startTime)} – ${formatChartTime(endTime)}`;
}

function formatModelName(modelVersion: string): string {
  if (modelVersion === "wesad_lr_v1_folded" || modelVersion === "wesad_logistic_regression_v1") {
    return "Logistic Regression";
  }
  return modelVersion;
}

export function computeCountdown(
  telemetry: Telemetry | null,
  points: ChartPoint[] | undefined,
  live: boolean,
  activeModel: boolean
): { countdown: number | null; graceCountdown: number | null; effectiveState?: EngineeringState } {
  if (!live || !activeModel || !telemetry) return { countdown: null, graceCountdown: null };
  const state = telemetry.prediction.state;
  if (state === "UNCERTAIN") return { countdown: null, graceCountdown: null };
  const lastPoint = points && points.length > 0 ? points[points.length - 1] : undefined;

  const isNoContact =
    (telemetry.schema_version === "1.2" && telemetry.signal_quality?.hr?.reason === "no_contact") ||
    Boolean(lastPoint?.hrNoContact);
  const hasGracePoint = Boolean(lastPoint?.noContactSeconds && lastPoint.noContactSeconds > 0);

  // Nếu telemetryStream đã xác nhận hết ân hạn (hoặc đang hiệu chuẩn thực sự), xử lý nhánh CALIBRATING trực tiếp
  const explicitlyCalibrating = state === "CALIBRATING" && lastPoint?.calibValidSeconds !== undefined;

  let trailingLen = 0;
  let firstDropTimeSec: number | undefined;
  let priorState: EngineeringState | undefined;
  if (!explicitlyCalibrating && points && points.length > 0) {
    for (let i = points.length - 1; i >= 0; i--) {
      const p = points[i];
      if (p.calibValidSeconds !== undefined) break;
      const pState = p.predictionState;
      if (pState === "UNCERTAIN") break;
      const isTrailingDrop =
        Boolean(p.hrNoContact) ||
        Boolean(p.noContactSeconds && p.noContactSeconds > 0) ||
        (state === "CALIBRATING" && pState === "CALIBRATING");
      if (isTrailingDrop) {
        trailingLen++;
        firstDropTimeSec = p.time;
      } else {
        priorState = pState;
        break;
      }
    }
  }

  const hasPriorActive = priorState === "NORMAL" || priorState === "ATTENTION";
  const elapsedFromFirstDrop =
    lastPoint && firstDropTimeSec !== undefined
      ? Math.max(0, Math.floor(lastPoint.time - firstDropTimeSec)) + 1
      : 0;
  const rawGraceCount =
    lastPoint?.noContactSeconds && lastPoint.noContactSeconds > 0
      ? Math.max(lastPoint.noContactSeconds, elapsedFromFirstDrop)
      : Math.max(trailingLen, elapsedFromFirstDrop);

  const isGraceFromActive =
    !explicitlyCalibrating &&
    (((state === "NORMAL" || state === "ATTENTION") && (isNoContact || hasGracePoint) && rawGraceCount <= 5) ||
      (state === "CALIBRATING" && hasPriorActive && rawGraceCount > 0));

  if (isGraceFromActive || state === "NORMAL" || state === "ATTENTION") {
    const inGrace =
      !explicitlyCalibrating &&
      (isNoContact || hasGracePoint || (state === "CALIBRATING" && hasPriorActive));
    const graceCount = inGrace ? Math.max(1, rawGraceCount || 1) : 0;

    if (inGrace && graceCount > 5) {
      return { countdown: 60, graceCountdown: null, effectiveState: "CALIBRATING" };
    }

    const effectiveState: EngineeringState =
      state === "NORMAL" || state === "ATTENTION" ? state : (priorState ?? "NORMAL");
    const graceCountdown = inGrace ? Math.max(1, 5 - Math.max(0, graceCount - 1)) : null;

    if (!points || points.length === 0) return { countdown: 10, graceCountdown, effectiveState };

    const activeEndIdx = Math.max(0, points.length - 1 - (inGrace ? trailingLen : 0));
    let calibEndIdx = -1;
    for (let i = activeEndIdx; i >= 0; i--) {
      const pState = points[i].predictionState;
      if (pState === "CALIBRATING" || (pState === undefined && points[i].probability == null)) {
        calibEndIdx = i;
        break;
      }
    }

    let activeElapsed = 0;
    if (calibEndIdx >= 0) {
      activeElapsed = activeEndIdx - (calibEndIdx + 1);
    } else {
      let lastProbChangeIdx = -1;
      const latestProb = points[activeEndIdx]?.probability;
      for (let i = activeEndIdx - 1; i >= 0; i--) {
        if (points[i].probability !== latestProb) {
          lastProbChangeIdx = i + 1;
          break;
        }
      }
      if (lastProbChangeIdx >= 0) {
        activeElapsed = activeEndIdx - lastProbChangeIdx;
      } else if (telemetry.timestamp_ms != null && Number.isFinite(telemetry.timestamp_ms) && !inGrace) {
        activeElapsed = Math.floor(telemetry.timestamp_ms / 1000) % 10;
      } else {
        activeElapsed = activeEndIdx % 10;
      }
    }

    const stepOffset = ((Math.max(0, activeElapsed) % 10) + 10) % 10;
    const remaining = 10 - stepOffset;
    return { countdown: Math.max(1, Math.min(10, remaining)), graceCountdown, effectiveState };
  }

  if (state === "CALIBRATING") {
    let noContactCount = 0;
    if (lastPoint?.noContactSeconds !== undefined && lastPoint.noContactSeconds > 0) {
      noContactCount = lastPoint.noContactSeconds;
    } else if (isNoContact && points && points.length > 0) {
      for (let i = points.length - 1; i >= 0; i--) {
        if (points[i].hrNoContact) noContactCount++;
        else break;
      }
    }
    if (isNoContact && noContactCount === 0) noContactCount = 1;

    if (lastPoint?.calibValidSeconds !== undefined) {
      const validCalibCount = lastPoint.calibValidSeconds;
      const countdown = Math.max(1, 60 - Math.max(0, validCalibCount - 1));
      const graceCountdown = isNoContact ? Math.max(1, 5 - Math.max(0, noContactCount - 1)) : null;
      return { countdown, graceCountdown, effectiveState: "CALIBRATING" };
    }

    let validCalibCount = 0;
    if (points && points.length > 0) {
      for (let i = points.length - 1; i >= 0; i--) {
        const p = points[i];
        const pState = p.predictionState;
        if (pState === "CALIBRATING" || (pState === undefined && p.probability == null)) {
          if (!p.hrNoContact) {
            validCalibCount++;
          }
        } else {
          break;
        }
      }
    }

    const countdown = Math.max(1, 60 - Math.max(0, validCalibCount - 1));
    const graceCountdown = isNoContact ? Math.max(1, 5 - Math.max(0, noContactCount - 1)) : null;
    return { countdown, graceCountdown, effectiveState: "CALIBRATING" };
  }

  return { countdown: null, graceCountdown: null };
}

export function PredictionPanel({ telemetry, points, live, onViewDetails, onResetAi }: {
  telemetry: Telemetry | null;
  points?: ChartPoint[];
  live: boolean;
  onViewDetails?: () => void;
  onResetAi?: () => Promise<void> | void;
}) {
  const [resettingAi, setResettingAi] = useState(false);
  const [resetFeedback, setResetFeedback] = useState<{ message: string; error: boolean } | null>(null);
  const deviceId = telemetry?.device_id;

  useEffect(() => {
    setResetFeedback(null);
  }, [deviceId]);

  useEffect(() => {
    if (!resetFeedback) return;
    const timer = window.setTimeout(() => setResetFeedback(null), 4000);
    return () => window.clearTimeout(timer);
  }, [resetFeedback]);

  const synthetic = telemetry?.data_origin === "SYNTHETIC";
  const hasModel = telemetry != null && telemetry.model_version !== "none";
  const status = !telemetry ? "Chờ dữ liệu" : !synthetic && !hasModel ? "Chưa có mô hình" : !live ? "Tạm ngưng" : synthetic ? "Giả lập" : "Đang hoạt động";
  const note = synthetic ? "Dữ liệu giả lập." : null;
  const activeModel = Boolean(hasModel || synthetic);
  const { countdown, graceCountdown, effectiveState } = computeCountdown(telemetry, points, live, activeModel);
  const displayState = effectiveState ?? telemetry?.prediction.state;
  const alert = live && (hasModel || synthetic) && displayState === "ATTENTION";
  const period = activePredictionPeriod(telemetry, points, live, activeModel, displayState);
  const canResetAi = Boolean(onResetAi && live && hasModel && !synthetic);

  const handleResetAi = async () => {
    if (!onResetAi || resettingAi) return;
    setResettingAi(true);
    setResetFeedback(null);
    try {
      await onResetAi();
      setResetFeedback({ message: "Đã đặt lại · hiệu chuẩn 60s.", error: false });
    } catch (error) {
      const code = error instanceof Error ? error.message : "";
      const message = code === "MQTT_UNAVAILABLE"
        ? "Chưa gửi được lệnh: thiết bị chưa sẵn sàng qua MQTT."
        : "Không thể đặt lại dữ liệu AI. Vui lòng thử lại.";
      setResetFeedback({ message, error: true });
    } finally {
      setResettingAi(false);
    }
  };

  return <section className="prediction-panel" aria-labelledby="prediction-heading">
    <div className="prediction-header">
      <PanelTitle id="prediction-heading" icon={BrainCircuit}>Dự đoán AI</PanelTitle>
      <span className="prediction-status" data-active={live && (hasModel || synthetic)}>{status}</span>
    </div>
    <div className="prediction-body">
      <div className="prediction-current">
        <StateCard state={displayState} probability={telemetry?.prediction.probability}
          period={period} countdown={countdown} graceCountdown={graceCountdown} modelVersion={telemetry?.model_version} live={live} synthetic={synthetic} />
        {note && <p className="prediction-note">{note}</p>}
        {hasModel && <p className="prediction-model">Mô hình: <span>{formatModelName(telemetry.model_version)}</span></p>}
        {(onResetAi || alert) && <div className="prediction-actions">
          {onResetAi && <button className="prediction-reset-button" type="button" disabled={!canResetAi || resettingAi}
            aria-busy={resettingAi} title={!canResetAi ? "Kết nối thiết bị đang chạy mô hình AI để đặt lại cửa sổ" : "Xóa bộ đệm 60 giây cũ và tính lại cửa sổ AI từ đầu"}
            onClick={handleResetAi}>
            <RotateCcw size={15} aria-hidden="true" />
            <span>{resettingAi ? "Đang đặt lại..." : "Đo lại cửa sổ 60s"}</span>
          </button>}
          {alert && <button className="prediction-details-button" type="button" onClick={onViewDetails}>Xem chi tiết</button>}
        </div>}
        {resetFeedback && <p className="prediction-reset-feedback" role={resetFeedback.error ? "alert" : "status"}
          data-error={resetFeedback.error}>{resetFeedback.message}</p>}
      </div>
    </div>
  </section>;
}

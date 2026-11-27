/** Hook thu thập dữ liệu sau phút thứ nhất (bỏ 60s hiệu chuẩn) và mở hộp gán nhãn khi tháo tay xong 5.2s.
 *  Thiết kế độc lập để dễ tháo bỏ khi không còn cần làm phong phú dataset.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { CaptureSamplePayload } from "../api/datasetCapture";
import type { Telemetry } from "../types/telemetry";

export interface PendingDatasetCapture {
  deviceId: string;
  sessionId: string | null;
  samples: CaptureSamplePayload[];
  durationSeconds: number;
}

export interface CaptureAccumulator {
  deviceId: string | null;
  sessionId: string | null;
  lastTimestampMs: number | null;
  dropSeconds: number;
  samples: CaptureSamplePayload[];
}

export const MIN_CAPTURE_SAMPLES = 5;

export function createEmptyAccumulator(): CaptureAccumulator {
  return { deviceId: null, sessionId: null, lastTimestampMs: null, dropSeconds: 0, samples: [] };
}

function flushPendingCapture(acc: CaptureAccumulator, telemetry: Telemetry): PendingDatasetCapture {
  const captured = [...acc.samples];
  const startMs = captured[0].timestamp_ms;
  const endMs = captured[captured.length - 1].timestamp_ms;
  const durationSeconds = Math.max(1, Math.round((endMs - startMs) / 1000) + 1);
  const result: PendingDatasetCapture = {
    deviceId: acc.deviceId ?? telemetry.device_id,
    sessionId: acc.sessionId ?? telemetry.session_id,
    samples: captured,
    durationSeconds,
  };
  acc.samples = [];
  acc.lastTimestampMs = null;
  acc.dropSeconds = 0;
  return result;
}

export function stepDatasetCapture(
  acc: CaptureAccumulator,
  telemetry: Telemetry | null,
  live: boolean,
): PendingDatasetCapture | null {
  if (!live || !telemetry || telemetry.data_origin !== "DEVICE") return null;

  const state = telemetry.prediction.state;
  const isNoContact =
    telemetry.schema_version === "1.2" && telemetry.signal_quality?.hr?.reason === "no_contact";

  // Đổi thiết bị hoặc đổi phiên -> xóa bộ đệm cũ chưa hoàn tất
  if (acc.deviceId && (acc.deviceId !== telemetry.device_id || acc.sessionId !== telemetry.session_id)) {
    acc.samples = [];
    acc.lastTimestampMs = null;
    acc.dropSeconds = 0;
  }

  // Khi đang ở NORMAL / ATTENTION nhưng tháo tay (no_contact) -> đếm giây ân hạn, không ghi thêm mẫu hỏng
  if ((state === "NORMAL" || state === "ATTENTION") && isNoContact) {
    if (acc.lastTimestampMs !== telemetry.timestamp_ms) {
      acc.lastTimestampMs = telemetry.timestamp_ms;
      acc.dropSeconds += 1;
    }
    return null;
  }

  // Bỏ qua 60 giây đầu đang hiệu chuẩn (CALIBRATING).
  // Tuy nhiên, nếu trước đó đã thu đủ mẫu sau hiệu chuẩn và vừa rớt sang CALIBRATING do tháo tay/hết 5s ân hạn,
  // thì đóng gói để bật khung gán nhãn thay vì xóa mất dữ liệu vừa thu.
  if (state === "CALIBRATING") {
    if (acc.samples.length >= MIN_CAPTURE_SAMPLES) {
      if (acc.lastTimestampMs !== telemetry.timestamp_ms) {
        acc.lastTimestampMs = telemetry.timestamp_ms;
        acc.dropSeconds += 1;
      }
      if (acc.dropSeconds >= 5) {
        return flushPendingCapture(acc, telemetry);
      }
      return null;
    }
    acc.deviceId = telemetry.device_id;
    acc.sessionId = telemetry.session_id;
    acc.samples = [];
    acc.lastTimestampMs = null;
    acc.dropSeconds = 0;
    return null;
  }

  // Sau khi đã đeo qua phút thứ nhất (NORMAL / ATTENTION) và đang tiếp xúc tay tốt -> thu mẫu
  if ((state === "NORMAL" || state === "ATTENTION") && !isNoContact) {
    if (acc.lastTimestampMs === telemetry.timestamp_ms) return null;
    acc.deviceId = telemetry.device_id;
    acc.sessionId = telemetry.session_id;
    acc.lastTimestampMs = telemetry.timestamp_ms;
    acc.dropSeconds = 0;
    acc.samples.push({
      timestamp_ms: telemetry.timestamp_ms,
      hr_bpm: telemetry.hr_bpm,
      gsr_raw: telemetry.gsr.raw,
      gsr_delta: telemetry.gsr.delta,
      ax: telemetry.schema_version !== "1.0" ? telemetry.movement.acceleration?.x ?? null : null,
      ay: telemetry.schema_version !== "1.0" ? telemetry.movement.acceleration?.y ?? null : null,
      az: telemetry.schema_version !== "1.0" ? telemetry.movement.acceleration?.z ?? null : null,
      gx: telemetry.schema_version !== "1.0" ? telemetry.movement.angular_velocity?.x ?? null : null,
      gy: telemetry.schema_version !== "1.0" ? telemetry.movement.angular_velocity?.y ?? null : null,
      gz: telemetry.schema_version !== "1.0" ? telemetry.movement.angular_velocity?.z ?? null : null,
    });
    return null;
  }

  // Khi tháo tay và hết 5.2s đếm ngược -> ESP32 chuyển về UNCERTAIN -> đóng gói dữ liệu để gán nhãn
  if (state === "UNCERTAIN" && acc.samples.length >= MIN_CAPTURE_SAMPLES) {
    return flushPendingCapture(acc, telemetry);
  }

  if (state === "UNCERTAIN") {
    acc.samples = [];
    acc.lastTimestampMs = null;
    acc.dropSeconds = 0;
  }
  return null;
}

export function useDatasetCapture(telemetry: Telemetry | null, live: boolean) {
  const accRef = useRef<CaptureAccumulator>(createEmptyAccumulator());
  const [pendingCapture, setPendingCapture] = useState<PendingDatasetCapture | null>(null);

  useEffect(() => {
    const ready = stepDatasetCapture(accRef.current, telemetry, live);
    if (ready) {
      setPendingCapture(ready);
    }
  }, [telemetry, live]);

  const dismissCapture = useCallback(() => setPendingCapture(null), []);
  const clearActiveCapture = useCallback(() => {
    accRef.current = createEmptyAccumulator();
  }, []);

  return { pendingCapture, dismissCapture, clearActiveCapture };
}

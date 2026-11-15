import type { EngineeringState } from "../types/telemetry";

const labels: Record<EngineeringState, string> = {
  NORMAL: "Bình thường", ATTENTION: "Cần chú ý",
  UNCERTAIN: "Chưa xác định", CALIBRATING: "Đang hiệu chuẩn",
};
export function StateCard({ state, probability, modelVersion, live = true, synthetic = false }: {
  state?: EngineeringState; probability?: number | null; modelVersion?: string; live?: boolean; synthetic?: boolean;
}) {
  const available = live && state !== undefined && (synthetic || (modelVersion !== undefined && modelVersion !== "none"));
  return <dl className="prediction-readings">
    <div>
      <dt>Trạng thái dự đoán</dt>
      <dd className="analysis-state" data-missing={!available} data-state={available ? state : undefined}>
        <strong>{available && state !== undefined ? labels[state] : "—"}</strong>
      </dd>
    </div>
    <div>
      <dt>Khoảng thời gian</dt>
      <dd className="prediction-period" data-missing="true">—</dd>
    </div>
    <div>
      <dt>Xác suất</dt>
      <dd className="prediction-probability" data-missing={!available || probability == null}>{available && probability != null ? `${Math.round(probability * 100)}%` : "—"}</dd>
    </div>
  </dl>;
}


import { BrainCircuit } from "lucide-react";
import type { Telemetry } from "../types/telemetry";
import { StateCard } from "./StateCard";
import { PanelTitle } from "./PanelTitle";

export function PredictionPanel({ telemetry, live, onViewDetails }: {
  telemetry: Telemetry | null; live: boolean; onViewDetails?: () => void;
}) {
  const synthetic = telemetry?.data_origin === "SYNTHETIC";
  const hasModel = telemetry != null && telemetry.model_version !== "none";
  const status = !telemetry ? "Chờ dữ liệu" : !synthetic && !hasModel ? "Chưa có mô hình" : !live ? "Tạm ngưng" : synthetic ? "Giả lập" : "Đang hoạt động";
  const note = synthetic ? "Dữ liệu giả lập." : !live ? null :
    !hasModel && !synthetic ? null :
    telemetry?.prediction.probability == null ? "Chưa đủ dữ liệu để đưa ra xác suất." :
    "Xác suất do mô hình cung cấp, không phải độ chính xác.";
  const alert = live && (hasModel || synthetic) && telemetry?.prediction.state === "ATTENTION";

  return <section className="prediction-panel" aria-labelledby="prediction-heading">
    <div className="prediction-header">
      <PanelTitle id="prediction-heading" icon={BrainCircuit}>Dự đoán AI</PanelTitle>
      <span className="prediction-status" data-active={live && (hasModel || synthetic)}>{status}</span>
    </div>
    <div className="prediction-body">
      <div className="prediction-current">
        <StateCard state={telemetry?.prediction.state} probability={telemetry?.prediction.probability}
          modelVersion={telemetry?.model_version} live={live} synthetic={synthetic} />
        {note && <p className="prediction-note">{note}</p>}
        {hasModel && <p className="prediction-model">Mô hình: <span>{telemetry.model_version}</span></p>}
        {alert && <button className="prediction-details-button" type="button" onClick={onViewDetails}>Xem chi tiết</button>}
      </div>
    </div>
  </section>;
}

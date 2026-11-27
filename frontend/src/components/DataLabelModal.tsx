import { useEffect, useState } from "react";
import {
  fetchDatasetCaptureSummary,
  saveDatasetCapture,
  type DatasetCaptureResponse,
  type DatasetCaptureSummary,
} from "../api/datasetCapture";
import type { PendingDatasetCapture } from "../hooks/useDatasetCapture";

function formatCaptureDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s} giây`;
  const mins = Math.floor(s / 60);
  const rem = s % 60;
  return rem === 0 ? `${mins} phút` : `${mins} phút ${rem} giây`;
}

export function DataLabelModal({
  capture,
  onClose,
  onSave = saveDatasetCapture,
  onLoadSummary = fetchDatasetCaptureSummary,
  initialSummary = null,
}: {
  capture: PendingDatasetCapture;
  onClose: () => void;
  onSave?: (payload: {
    device_id: string;
    session_id: string | null;
    label: 0 | 1;
    samples: PendingDatasetCapture["samples"];
  }) => Promise<DatasetCaptureResponse>;
  onLoadSummary?: () => Promise<DatasetCaptureSummary>;
  initialSummary?: DatasetCaptureSummary | null;
}) {
  const [label, setLabel] = useState<0 | 1>(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedResult, setSavedResult] = useState<DatasetCaptureResponse | null>(null);
  const [summary, setSummary] = useState<DatasetCaptureSummary | null>(initialSummary);

  useEffect(() => {
    let active = true;
    onLoadSummary()
      .then(data => {
        if (active) setSummary(data);
      })
      .catch(() => {
        // Giữ nguyên trạng thái mặc định nếu chưa tải được lịch sử đợt
      });
    return () => {
      active = false;
    };
  }, [onLoadSummary, capture]);

  const currentBatch = summary ? summary.next_batch_number : 1;
  const previousBatch = summary?.previous_batch ?? null;
  const totalSamplesBefore = summary ? summary.total_samples_before : 0;

  const handleSubmit = async () => {
    if (saving) return;
    setSaving(true);
    setError(null);
    try {
      const result = await onSave({
        device_id: capture.deviceId,
        session_id: capture.sessionId,
        label,
        samples: capture.samples,
      });
      setSavedResult(result);
      window.setTimeout(onClose, 900);
    } catch {
      setError("Không lưu được dữ liệu. Kiểm tra backend rồi thử lại.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="capture-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="capture-modal-title">
      <div className="capture-modal-card">
        <div className="capture-modal-header">
          <h2 id="capture-modal-title" className="capture-modal-title">Gán nhãn dữ liệu vừa thu</h2>
          <span className="capture-batch-badge">Đợt {currentBatch}</span>
        </div>
        <p className="capture-modal-subtitle">
          Đã tự động loại bỏ 60 giây hiệu chuẩn đầu tiên để đảm bảo tín hiệu ổn định.
        </p>

        <dl className="capture-modal-stats">
          <div>
            <dt>Thời gian đợt này</dt>
            <dd>{formatCaptureDuration(capture.durationSeconds)}</dd>
          </div>
          <div>
            <dt>Số mẫu đợt này</dt>
            <dd>{capture.samples.length} mẫu</dd>
          </div>
        </dl>

        <dl className="capture-modal-history">
          <div>
            <dt>{previousBatch ? `Đợt trước (Đợt ${previousBatch.batch_number})` : "Đợt trước"}</dt>
            <dd>
              {previousBatch
                ? `${formatCaptureDuration(previousBatch.duration_seconds)} · ${previousBatch.sample_count} mẫu`
                : "Chưa có"}
            </dd>
          </div>
          <div>
            <dt>Tổng mẫu đã lưu (trước đợt này)</dt>
            <dd>{totalSamplesBefore} mẫu</dd>
          </div>
        </dl>

        <div className="capture-modal-field">
          <label htmlFor="capture-label-select">Nhãn trạng thái</label>
          <select
            id="capture-label-select"
            value={String(label)}
            disabled={saving || savedResult !== null}
            onChange={event => setLabel(event.target.value === "1" ? 1 : 0)}
          >
            <option value="0">No stress</option>
            <option value="1">Stress</option>
          </select>
        </div>

        {error && <p className="capture-modal-feedback" role="alert" data-error="true">{error}</p>}
        {savedResult && (
          <p className="capture-modal-feedback" role="status" data-error="false">
            Đã lưu Đợt {currentBatch}: {savedResult.window_count} cửa sổ ({savedResult.sample_count} mẫu).
          </p>
        )}

        <div className="capture-modal-actions">
          <button type="button" className="capture-btn-secondary" disabled={saving} onClick={onClose}>
            Bỏ qua
          </button>
          <button
            type="button"
            className="capture-btn-primary"
            disabled={saving || savedResult !== null}
            onClick={handleSubmit}
          >
            {saving ? "Đang lưu..." : savedResult ? "Đã lưu" : "Lưu dữ liệu"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { saveDatasetCapture, type DatasetCaptureResponse } from "../api/datasetCapture";
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
}: {
  capture: PendingDatasetCapture;
  onClose: () => void;
  onSave?: (payload: {
    device_id: string;
    session_id: string | null;
    label: 0 | 1;
    samples: PendingDatasetCapture["samples"];
  }) => Promise<DatasetCaptureResponse>;
}) {
  const [label, setLabel] = useState<0 | 1>(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedResult, setSavedResult] = useState<DatasetCaptureResponse | null>(null);

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
        <h2 id="capture-modal-title" className="capture-modal-title">Gán nhãn dữ liệu vừa thu</h2>
        <p className="capture-modal-subtitle">
          Đã tự động loại bỏ 60 giây hiệu chuẩn đầu tiên để đảm bảo tín hiệu ổn định.
        </p>

        <dl className="capture-modal-stats">
          <div>
            <dt>Tổng thời gian thu</dt>
            <dd>{formatCaptureDuration(capture.durationSeconds)}</dd>
          </div>
          <div>
            <dt>Tổng số mẫu</dt>
            <dd>{capture.samples.length} mẫu</dd>
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
            <option value="0">Không stress (No stress)</option>
            <option value="1">Stress</option>
          </select>
        </div>

        {error && <p className="capture-modal-feedback" role="alert" data-error="true">{error}</p>}
        {savedResult && (
          <p className="capture-modal-feedback" role="status" data-error="false">
            Đã lưu {savedResult.window_count} cửa sổ ({savedResult.sample_count} mẫu) vào {savedResult.dataset_file}.
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

import { useEffect, useState } from "react";
import {
  fetchDatasetCaptureSummary,
  saveDatasetCapture,
  type CaptureContext,
  type DatasetCaptureRequest,
  type DatasetCaptureResponse,
  type DatasetCaptureSummary,
} from "../api/datasetCapture";
import type { PendingDatasetCapture } from "../hooks/useDatasetCapture";

const DEFAULT_SUBJECT_PRESETS = ["REAL_P01", "REAL_P02", "REAL_P03"];

const CONTEXT_OPTIONS: Record<0 | 1, Array<{ value: CaptureContext; label: string }>> = {
  0: [
    { value: "rest", label: "Ngồi yên / thư giãn" },
    { value: "active", label: "Vận động bình thường" },
  ],
  1: [
    { value: "stress_mild", label: "Căng thẳng nhẹ" },
    { value: "stress_high", label: "Căng thẳng mạnh" },
  ],
};

function formatCaptureDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s} giây`;
  const mins = Math.floor(s / 60);
  const rem = s % 60;
  return rem === 0 ? `${mins} phút` : `${mins} phút ${rem} giây`;
}

function sanitizeSubjectId(raw: string): string {
  return raw.trim().replace(/[^A-Za-z0-9_-]/g, "");
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
  onSave?: (payload: DatasetCaptureRequest) => Promise<DatasetCaptureResponse>;
  onLoadSummary?: () => Promise<DatasetCaptureSummary>;
  initialSummary?: DatasetCaptureSummary | null;
}) {
  const [label, setLabel] = useState<0 | 1>(0);
  const [context, setContext] = useState<CaptureContext>("rest");
  const [subjectId, setSubjectId] = useState<string>(initialSummary?.last_subject_id || "REAL_P01");
  const [subjectTouched, setSubjectTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedResult, setSavedResult] = useState<DatasetCaptureResponse | null>(null);
  const [summary, setSummary] = useState<DatasetCaptureSummary | null>(initialSummary);

  useEffect(() => {
    let active = true;
    onLoadSummary()
      .then(data => {
        if (!active) return;
        setSummary(data);
        if (!subjectTouched && data.last_subject_id) {
          setSubjectId(data.last_subject_id);
        }
      })
      .catch(() => {
        // Giữ nguyên trạng thái mặc định nếu chưa tải được lịch sử đợt
      });
    return () => {
      active = false;
    };
  }, [onLoadSummary, capture, subjectTouched]);

  const currentBatch = summary ? summary.next_batch_number : 1;
  const previousBatch = summary?.previous_batch ?? null;
  const totalSamplesBefore = summary ? summary.total_samples_before : 0;
  const subjectPresets = Array.from(
    new Set([...(summary?.known_subject_ids ?? []), ...DEFAULT_SUBJECT_PRESETS]),
  ).slice(0, 5);

  const handleLabelChange = (nextLabel: 0 | 1) => {
    setLabel(nextLabel);
    setContext(CONTEXT_OPTIONS[nextLabel][0].value);
  };

  const handleSubmit = async () => {
    if (saving) return;
    const cleanedSubject = sanitizeSubjectId(subjectId) || "REAL_P01";
    setSaving(true);
    setError(null);
    try {
      const result = await onSave({
        device_id: capture.deviceId,
        session_id: capture.sessionId,
        subject_id: cleanedSubject,
        context,
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

        <div className="capture-modal-row">
          <div className="capture-modal-field">
            <label htmlFor="capture-label-select">Nhãn trạng thái</label>
            <select
              id="capture-label-select"
              value={String(label)}
              disabled={saving || savedResult !== null}
              onChange={event => handleLabelChange(event.target.value === "1" ? 1 : 0)}
            >
              <option value="0">No stress</option>
              <option value="1">Stress</option>
            </select>
          </div>

          <div className="capture-modal-field">
            <label htmlFor="capture-context-select">Ngữ cảnh</label>
            <select
              id="capture-context-select"
              value={context}
              disabled={saving || savedResult !== null}
              onChange={event => setContext(event.target.value as CaptureContext)}
            >
              {CONTEXT_OPTIONS[label].map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="capture-modal-field">
          <label htmlFor="capture-subject-input">Người đeo (Subject ID)</label>
          <input
            id="capture-subject-input"
            type="text"
            value={subjectId}
            maxLength={32}
            disabled={saving || savedResult !== null}
            placeholder="REAL_P01"
            onChange={event => {
              setSubjectTouched(true);
              setSubjectId(event.target.value);
            }}
          />
          <div className="capture-subject-chips" role="group" aria-label="Chọn nhanh người đeo">
            {subjectPresets.map(preset => (
              <button
                key={preset}
                type="button"
                className="capture-subject-chip"
                data-active={sanitizeSubjectId(subjectId) === preset}
                disabled={saving || savedResult !== null}
                onClick={() => {
                  setSubjectTouched(true);
                  setSubjectId(preset);
                }}
              >
                {preset}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="capture-modal-feedback" role="alert" data-error="true">{error}</p>}
        {savedResult && (
          <p className="capture-modal-feedback" role="status" data-error="false">
            Đã lưu Đợt {currentBatch} ({savedResult.subject_id}): {savedResult.window_count} cửa sổ ({savedResult.sample_count} mẫu).
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

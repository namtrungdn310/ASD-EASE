import type { QualityReading, QualityReason } from "../types/telemetry";

const reasons: Record<QualityReason, string> = {
  ok: "Thu mẫu tốt",
  warming_up: "Đang đánh giá",
  stale: "Không có mẫu mới",
  no_contact: "Chưa tiếp xúc",
  motion: "Đang chuyển động",
  saturated: "Chạm giới hạn",
  missing_samples: "Thiếu mẫu",
  weak_signal: "Sóng chưa rõ",
  calibrating: "Đang hiệu chỉnh",
  unavailable: "Chưa đánh giá",
};

export function MetricQuality({ reading, live }: { reading?: QualityReading; live: boolean }) {
  const sampleCount = live ? reading?.sample_count ?? null : null;
  const score = live ? reading?.score : null;
  const note = !live ? "Không có dữ liệu mới" : reading ? reasons[reading.reason] : "Chưa đánh giá";
  const percent = score == null ? null : Math.round(score * 100);
  const text = percent == null ? "—" : `${percent}%`;
  const description = `Số mẫu cảm biến thực thu trong 8 giây đã hoàn tất: ${sampleCount ?? "chưa có dữ liệu"}. HR đếm mẫu PPG, không phải số nhịp tim; gia tốc và tốc độ xoay dùng cùng mẫu IMU. Chất lượng tín hiệu ${text}, cùng cửa sổ 8 giây. ${note}. Thu đủ mẫu không đồng nghĩa tín hiệu tốt hoặc số đo chính xác.`;
  return <span className="metric-quality" role="img"
    aria-label={description} title={description}
    data-level={percent == null ? "unknown" : percent >= 80 ? "high" : percent >= 50 ? "medium" : "low"}>
    <span className="metric-sample-count" data-missing={sampleCount == null} aria-hidden="true">{sampleCount ?? "—"} mẫu</span>
    <span className="metric-quality-divider" aria-hidden="true">·</span>
    <strong data-missing={percent == null} aria-hidden="true">{text}</strong>
  </span>;
}

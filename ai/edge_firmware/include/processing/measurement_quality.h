#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace asd {
// Điểm kỹ thuật v1, không phải xác suất số đo đúng. -1 nội bộ = chưa đánh giá.
enum class QualityReason : uint8_t {
  Ok, WarmingUp, Stale, NoContact, Motion, Saturated, MissingSamples,
  WeakSignal, Calibrating, Unavailable
};
struct MeasurementQuality {
  float score = -1;
  QualityReason reason = QualityReason::WarmingUp;
  int32_t sampleCount = -1;
};
inline const char* qualityReasonName(QualityReason reason) {
  switch (reason) {
    case QualityReason::Ok: return "ok";
    case QualityReason::Stale: return "stale";
    case QualityReason::NoContact: return "no_contact";
    case QualityReason::Motion: return "motion";
    case QualityReason::Saturated: return "saturated";
    case QualityReason::MissingSamples: return "missing_samples";
    case QualityReason::WeakSignal: return "weak_signal";
    case QualityReason::Calibrating: return "calibrating";
    case QualityReason::Unavailable: return "unavailable";
    default: return "warming_up";
  }
}

// 8 giây đã hoàn tất + bucket giây hiện tại. Không đếm lại cache read().
// Chỉ theo dõi số mẫu/chạm rail; không phạt chuyển động hoặc thay đổi sinh lý thật.
class QualityWindow {
 public:
  void reset(){*this=QualityWindow{};}
  void add(uint64_t at, bool saturated) {
    if (started_ && at <= last_) return;
    if (!started_) { first_ = at; started_ = true; }
    last_ = at;
    const uint64_t second = at / 1000;
    auto& bucket = buckets_[second % buckets_.size()];
    if (!bucket.used || bucket.second != second) bucket = {second, 0, 0, true};
    ++bucket.samples;
    if (saturated) ++bucket.saturated;
  }
  MeasurementQuality evaluate(uint64_t now, uint32_t rate) const {
    if (!started_) return {};
    const uint64_t end = now / 1000;
    uint32_t samples = 0, saturated = 0;
    for (const auto& bucket : buckets_) {
      if (bucket.used && bucket.second < end && end - bucket.second <= 8) {
        samples += bucket.samples; saturated += bucket.saturated;
      }
    }
    if (now < last_ || now - last_ > 1000) return {-1, QualityReason::Stale, static_cast<int32_t>(samples)};
    if (!rate || end < 8 || first_ > (end - 8) * 1000)
      return {-1, QualityReason::WarmingUp, static_cast<int32_t>(samples)};
    const float expected = float(rate) * 8;
    const float coverage = std::min(1.f, samples / expected);
    const float usable = samples ? 1.f - float(saturated) / samples : 0;
    return {coverage * usable, saturated ? QualityReason::Saturated :
      coverage < .98f ? QualityReason::MissingSamples : QualityReason::Ok, static_cast<int32_t>(samples)};
  }
 private:
  struct Bucket { uint64_t second = 0; uint32_t samples = 0, saturated = 0; bool used = false; };
  std::array<Bucket, 9> buckets_{};
  uint64_t first_ = 0, last_ = 0;
  bool started_ = false;
};

inline MeasurementQuality opticalQuality(MeasurementQuality acquisition, bool contact,
    bool settled, bool motionAllowed, bool overloaded, bool analysisFresh, float evidence) {
  if (acquisition.reason == QualityReason::Stale) return acquisition;
  if (overloaded) return {0, QualityReason::Saturated};
  if (!contact) return {0, QualityReason::NoContact};
  if (!settled) return {-1, QualityReason::WarmingUp};
  if (!motionAllowed) return {0, QualityReason::Motion};
  if (acquisition.score < 0) return acquisition;
  if (!analysisFresh || !std::isfinite(evidence)) return {-1, QualityReason::Unavailable};
  // Evidence đã tổng hợp phổ, tự tương quan, độ lặp hình dạng từ sóng thực.
  // Không dùng posterior/massScore hay giá trị HR đã làm mượt/dự báo.
  const float waveform = std::max(0.f, std::min(1.f, evidence));
  acquisition.score *= waveform;
  if (acquisition.reason == QualityReason::Ok && waveform < .5f)
    acquisition.reason = QualityReason::WeakSignal;
  return acquisition;
}
}  // namespace asd

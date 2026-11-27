#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace asd {

// =============================================================================
// Bộ lọc HR ổn định cho cả biểu đồ (Phương án B) và đầu vào AI:
// - Loại bỏ gai nhảy vọt (vd: 80 -> 150 rồi hạ dần) hoặc tụt sâu (80 -> 45 rồi tăng dần)
// - Chấp nhận nhịp tăng/giảm sinh lý mượt (<= 4.5 bpm/s) hoặc mức nền mới giữ ổn định >= 4s
// - Khi tạm ẩn nhịp nhiễu (vẫn đeo tay), giữ nguyên mốc lastStableAtMs_ tối đa 15s
//   để biểu đồ Frontend nối liền bằng nét vàng đứt đoạn.
// =============================================================================
class HrStabilityFilter {
 public:
  void reset() { *this = HrStabilityFilter{}; }

  void update(uint64_t nowMs, bool fingerDetected, bool rawValid, float rawBpm,
              uint64_t rawMeasuredAtMs) {
    if (!fingerDetected) {
      if (noFingerSinceMs_ == 0) {
        noFingerSinceMs_ = nowMs;
      }
      if (nowMs >= noFingerSinceMs_ && (nowMs - noFingerSinceMs_) >= kNoContactResetMs) {
        reset();
      } else {
        freshStable_ = false;
      }
      return;
    }
    noFingerSinceMs_ = 0;

    if (!rawValid || !std::isfinite(rawBpm) || rawBpm < 40.0f || rawBpm > 200.0f ||
        rawMeasuredAtMs == 0) {
      freshStable_ = false;
      return;
    }

    if (rawMeasuredAtMs == lastProcessedRawMs_) {
      // Không có mẫu mới từ driver: giữ trạng thái freshStable_ trong hạn 3s
      if (freshStable_ && (nowMs < lastStableAtMs_ || (nowMs - lastStableAtMs_) > kFreshMaxAgeMs)) {
        freshStable_ = false;
      }
      return;
    }

    const float dtSec = (lastProcessedRawMs_ > 0 && rawMeasuredAtMs > lastProcessedRawMs_)
                            ? std::max(0.5f, static_cast<float>(rawMeasuredAtMs - lastProcessedRawMs_) / 1000.0f)
                            : 1.0f;
    lastProcessedRawMs_ = rawMeasuredAtMs;
    pushRawHistory(rawBpm);

    if (!hasAnchor_) {
      // Cần ít nhất 3 mẫu liên tiếp dao động hẹp (<= 10 bpm) để khóa mốc ổn định đầu tiên
      if (candCount_ == 0 ||
          (std::fabs(rawBpm - prevRawBpm_) <= 6.0f * dtSec && std::fabs(rawBpm - prevRawBpm_) <= 8.0f)) {
        pushCandidate(rawBpm);
      } else {
        candCount_ = 0;
        pushCandidate(rawBpm);
      }
      prevRawBpm_ = rawBpm;

      if (candCount_ >= 3 && candidateSpan(3) <= 10.0f) {
        hasAnchor_ = true;
        anchorBpm_ = candidateMean(3);
        stableBpm_ = rawBpm;
        lastStableAtMs_ = rawMeasuredAtMs;
        freshStable_ = true;
      } else {
        freshStable_ = false;
      }
      return;
    }

    const float stepDiff = std::fabs(rawBpm - prevRawBpm_);
    const float ratePerSec = stepDiff / dtSec;
    const float med7 = rawMedian();
    const float anchorDiff = std::fabs(rawBpm - anchorBpm_);
    const float medDiff = std::fabs(rawBpm - med7);
    prevRawBpm_ = rawBpm;

    // 1. Chặn bước nhảy tốc độ phi sinh lý hoặc gai tách khỏi đường trung vị/nền
    const bool stepTooFast = (ratePerSec > 5.0f) || (stepDiff > 9.0f);
    const bool obviousOutlier = (anchorDiff > 18.0f && medDiff > 10.0f);
    if (stepTooFast || obviousOutlier) {
      candCount_ = 0;
      if (!obviousOutlier) {
        pushCandidate(rawBpm);
      }
      freshStable_ = false;
      return;
    }

    // 2. Gom chuỗi mượt
    pushCandidate(rawBpm);

    // Nếu nằm gần nền ổn định hiện tại và mượt >= 2 nhịp -> chấp nhận ngay
    if (anchorDiff <= 14.0f && candCount_ >= 2 && candidateSpan(2) <= 8.0f) {
      freshStable_ = true;
      stableBpm_ = rawBpm;
      lastStableAtMs_ = rawMeasuredAtMs;
      anchorBpm_ = 0.80f * anchorBpm_ + 0.20f * rawBpm;
      return;
    }

    // Nếu là mức nhịp mới thật sự (vd: căng thẳng tăng cao ổn định) giữ mượt >= 4 nhịp liên tiếp
    if (candCount_ >= 4 && candidateSpan(4) <= 8.0f) {
      freshStable_ = true;
      stableBpm_ = rawBpm;
      lastStableAtMs_ = rawMeasuredAtMs;
      anchorBpm_ = candidateMean(4);
      return;
    }

    // Đang trong đoạn quá độ hồi phục sau nhảy/tụt -> tạm ẩn nét xanh, chờ ổn định hẳn
    freshStable_ = false;
  }

  bool isFreshStable(uint64_t nowMs) const {
    return freshStable_ && lastStableAtMs_ > 0 && nowMs >= lastStableAtMs_ &&
           (nowMs - lastStableAtMs_) <= kFreshMaxAgeMs;
  }

  float stableBpm() const { return stableBpm_; }
  uint64_t lastStableAtMs() const { return lastStableAtMs_; }
  float anchorBpm() const { return anchorBpm_; }
  bool hasAnchor() const { return hasAnchor_; }

 private:
  static constexpr uint64_t kFreshMaxAgeMs = 3000ULL;
  static constexpr uint64_t kNoContactResetMs = 5000ULL;
  static constexpr size_t kRawHistMax = 7;
  static constexpr size_t kCandMax = 4;

  void pushRawHistory(float v) {
    rawHist_[rawHead_] = v;
    rawHead_ = (rawHead_ + 1) % kRawHistMax;
    if (rawCount_ < kRawHistMax) ++rawCount_;
  }

  float rawMedian() const {
    if (rawCount_ == 0) return anchorBpm_;
    std::array<float, kRawHistMax> tmp{};
    for (size_t i = 0; i < rawCount_; ++i) tmp[i] = rawHist_[i];
    std::sort(tmp.begin(), tmp.begin() + rawCount_);
    return tmp[rawCount_ / 2];
  }

  void pushCandidate(float v) {
    if (candCount_ < kCandMax) {
      candVals_[candCount_++] = v;
    } else {
      for (size_t i = 1; i < kCandMax; ++i) candVals_[i - 1] = candVals_[i];
      candVals_[kCandMax - 1] = v;
    }
  }

  float candidateSpan(size_t count) const {
    const size_t n = std::min(count, candCount_);
    if (n == 0) return 0.0f;
    float lo = candVals_[candCount_ - n], hi = lo;
    for (size_t i = candCount_ - n + 1; i < candCount_; ++i) {
      if (candVals_[i] < lo) lo = candVals_[i];
      if (candVals_[i] > hi) hi = candVals_[i];
    }
    return hi - lo;
  }

  float candidateMean(size_t count) const {
    const size_t n = std::min(count, candCount_);
    if (n == 0) return anchorBpm_;
    float sum = 0.0f;
    for (size_t i = candCount_ - n; i < candCount_; ++i) sum += candVals_[i];
    return sum / static_cast<float>(n);
  }

  std::array<float, kRawHistMax> rawHist_{};
  size_t rawHead_ = 0, rawCount_ = 0;
  std::array<float, kCandMax> candVals_{};
  size_t candCount_ = 0;

  bool hasAnchor_ = false;
  bool freshStable_ = false;
  float anchorBpm_ = 75.0f;
  float stableBpm_ = 0.0f;
  float prevRawBpm_ = 0.0f;
  uint64_t lastProcessedRawMs_ = 0;
  uint64_t lastStableAtMs_ = 0;
  uint64_t noFingerSinceMs_ = 0;
};

}  // namespace asd

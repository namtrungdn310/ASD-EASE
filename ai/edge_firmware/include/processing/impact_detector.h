#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <array>

namespace asd {

// =============================================================================
// Bộ phát hiện xung va đập (đập bàn 1 lần vs nhiều lần) ở tần số IMU gốc 50 Hz:
// - Xung đập bàn tạo gia tốc động tức thời cao (>= 5.5 m/s²) kèm độ giật Jerk lớn
//   (>= 4.0 m/s² mỗi 20ms) và tắt nhanh, khác với vung tay/đi lại nhịp chậm.
// - Thời gian chống dội refractory 300 ms để không đếm nhầm dư chấn mặt bàn thành nhiều lần.
// - Đập 1 lần đơn lẻ trong 60s -> đánh dấu lọc nhiễu ACC (không tự kích stress).
// - Đập >= 3 lần trong 30s -> đánh dấu hành vi đập lặp lại.
// =============================================================================
class ImpactDetector {
 public:
  void reset() { *this = ImpactDetector{}; }

  // Chỉ xóa lịch sử va đập cũ khi reset cửa sổ AI, giữ nguyên nền trọng lực của IMU
  void clearHistory() {
    impactTimes_.fill(0);
    impactHead_ = 0;
    impactCount_ = 0;
    lastImpactMs_ = 0;
    suppressUntilMs_ = 0;
  }

  void update(uint64_t sampleMs, bool valid, float ax, float ay, float az) {
    if (!valid || sampleMs == 0 || sampleMs <= lastSampleMs_) return;
    if (!std::isfinite(ax) || !std::isfinite(ay) || !std::isfinite(az)) return;

    const float norm = std::sqrt(ax * ax + ay * ay + az * az);
    if (!initialized_) {
      baseNorm_ = norm;
      prevNorm_ = norm;
      lastSampleMs_ = sampleMs;
      initialized_ = true;
      return;
    }

    const float dyn = std::fabs(norm - baseNorm_);
    const float jerk = std::fabs(norm - prevNorm_);
    prevNorm_ = norm;
    lastSampleMs_ = sampleMs;

    // Chỉ cập nhật nền trọng lực khi không trong pha xung va đập mạnh
    if (dyn < 3.0f) {
      baseNorm_ = 0.94f * baseNorm_ + 0.06f * norm;
    }

    const bool refractoryClear = (lastImpactMs_ == 0) || (sampleMs - lastImpactMs_ >= kRefractoryMs);
    if (refractoryClear && dyn >= kImpactDynThreshold && jerk >= kImpactJerkThreshold) {
      lastImpactMs_ = sampleMs;
      suppressUntilMs_ = sampleMs + kSingleBumpSuppressMs;
      impactTimes_[impactHead_] = sampleMs;
      impactHead_ = (impactHead_ + 1) % kMaxImpacts;
      if (impactCount_ < kMaxImpacts) ++impactCount_;
    }
  }

  // Đang nằm trong đuôi xung va đập ngắn (0.45s) -> cho phép lọc bỏ nếu chỉ là đập 1 lần
  bool inSingleImpactTransient(uint64_t nowMs) const {
    return nowMs <= suppressUntilMs_ && countWithin(nowMs, 30000ULL) <= 1;
  }

  uint8_t countWithin(uint64_t nowMs, uint64_t windowMs) const {
    uint8_t count = 0;
    for (size_t i = 0; i < impactCount_; ++i) {
      const uint64_t t = impactTimes_[i];
      if (t > 0 && nowMs >= t && (nowMs - t) <= windowMs) {
        ++count;
      }
    }
    return count;
  }

  bool hasRepeatedImpact(uint64_t nowMs) const {
    return countWithin(nowMs, 30000ULL) >= 3;
  }

 private:
  static constexpr uint64_t kRefractoryMs = 300ULL;
  static constexpr uint64_t kSingleBumpSuppressMs = 450ULL;
  static constexpr float kImpactDynThreshold = 5.5f;   // m/s^2 lệch khỏi nền trọng lực
  static constexpr float kImpactJerkThreshold = 4.0f;  // m/s^2 bước nhảy tức thời @ 50Hz
  static constexpr size_t kMaxImpacts = 16;

  bool initialized_ = false;
  float baseNorm_ = 9.80665f;
  float prevNorm_ = 9.80665f;
  uint64_t lastSampleMs_ = 0;
  uint64_t lastImpactMs_ = 0;
  uint64_t suppressUntilMs_ = 0;

  std::array<uint64_t, kMaxImpacts> impactTimes_{};
  size_t impactHead_ = 0;
  size_t impactCount_ = 0;
};

}  // namespace asd

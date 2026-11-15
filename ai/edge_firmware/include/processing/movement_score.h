#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <initializer_list>

namespace asd {
// motion-rms-v1: chỉ số kỹ thuật, không phải kết quả phân loại AI.
// Định nghĩa/tham số: docs/contracts/MOVEMENT_SCORE.md.
class MovementScoreEstimator {
 public:
  struct Reading { float score = 0; bool valid = false; };

  void reset() {
    count_ = next_ = 0;
    energySum_ = 0;
    hasTime_ = false;
    reading_ = {};
  }

  Reading update(uint64_t now, float ax, float ay, float az,
                 float gx, float gy, float gz) {
    // Dữ liệu trước EMA: m/s² và degrees/s, thang MPU hiện tại ±2g/±250°/s.
    for (float axis : {ax, ay, az}) {
      if (!std::isfinite(axis) || std::fabs(axis) >= 19.60f) { reset(); return {}; }
    }
    for (float axis : {gx, gy, gz}) {
      if (!std::isfinite(axis) || std::fabs(axis) >= 249.9f) { reset(); return {}; }
    }
    if (hasTime_) {
      if (now == lastTime_) return reading_; // Cache không được tính là mẫu mới.
      if (now < lastTime_ || now - lastTime_ > 100) reset();
    }
    lastTime_ = now;
    hasTime_ = true;
    const float acceleration = std::sqrt(ax * ax + ay * ay + az * az);
    const float rotation = std::sqrt(gx * gx + gy * gy + gz * gz);
    const float a = std::max(0.0f, std::fabs(acceleration - 9.80665f) - 0.15f) / 2.0f;
    const float w = std::max(0.0f, rotation - 3.0f) / 90.0f;
    const float energy = a * a + w * w;
    if (count_ == kSamples) energySum_ -= energies_[next_];
    else ++count_;
    energies_[next_] = energy;
    times_[next_] = now;
    energySum_ += energy;
    next_ = (next_ + 1) % kSamples;

    // 50 mẫu ở 50Hz có span danh định980ms; dung sai có giới hạn.
    const uint64_t span = now - times_[(next_ + kSamples - count_) % kSamples];
    reading_ = {};
    if (count_ == kSamples && span >= 800 && span <= 1200) {
      const double rms = std::sqrt(std::max(0.0, energySum_ / count_));
      reading_.score = static_cast<float>(rms / (1.0 + rms));
      reading_.valid = true;
    }
    return reading_;
  }

 private:
  static constexpr size_t kSamples = 50;
  std::array<float, kSamples> energies_{};
  std::array<uint64_t, kSamples> times_{};
  size_t count_ = 0, next_ = 0;
  double energySum_ = 0;
  uint64_t lastTime_ = 0;
  bool hasTime_ = false;
  Reading reading_{};
};
} // namespace asd

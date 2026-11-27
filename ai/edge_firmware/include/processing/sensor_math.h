#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>

namespace asd {

struct SampleBatchTime { uint64_t first = 0; bool gap = false; };
// Không có chân INT: giữ khoảng danh định trong FIFO, sai số pha vẫn tới một chu kỳ.
class SampleClock {
 public:
  explicit SampleClock(bool trackSmallDrift=false) : trackSmallDrift_(trackSmallDrift) {}
  void reset() { last_ = lastCaptured_ = 0; initialized_ = false; }
  SampleBatchTime batch(uint64_t captured, uint32_t count, uint32_t period) {
    SampleBatchTime result;
    if (count == 0 || period == 0 || uint64_t(count - 1)*period > captured) {
      result.gap = true; reset(); return result;
    }
    const uint64_t span = uint64_t(count - 1) * period;
    result.first = captured - span;
    if (initialized_) {
      const uint64_t expected = last_ + uint64_t(count) * period;
      if (trackSmallDrift_ && (captured<=lastCaptured_ ||
          captured-lastCaptured_>(uint64_t(count)+2)*period)) result.gap=true;
      else if (expected <= captured && captured - expected <= 3*period) {
        result.first = last_ + period;
        // Bản thử PPG: bám chậm pha đọc, tối đa1ms/lô, không tạo mốc tương lai.
        // Giữ cùng ngưỡng gap lớn; không đổi timestamp các mẫu trong lô.
        if (trackSmallDrift_ && captured>expected) ++result.first;
      }
      else if (expected > captured && expected - captured <= period && result.first > last_) {
        // Poll đến sớm hơn pha ước tính: neo về thực tại, không tạo timestamp tương lai.
      } else result.gap = true;
    }
    last_ = result.first + span; lastCaptured_=captured; initialized_ = true;
    return result;
  }
 private:
  uint64_t last_ = 0;
  uint64_t lastCaptured_ = 0;
  bool initialized_ = false;
  bool trackSmallDrift_ = false;
};

struct LowPassCoefficients { float b0, b1, b2, a1, a2; };
inline LowPassCoefficients lowPass(float cutoff, float rate) {
  const float k = std::tan(3.14159265358979323846f * cutoff / rate);
  const float norm = 1 / (1 + 1.4142135623730951f*k + k*k);
  return {k*k*norm, 2*k*k*norm, k*k*norm, 2*(k*k-1)*norm,
          (1 - 1.4142135623730951f*k + k*k)*norm};
}

// Giữ pha lịch; không giả tạo mẫu để bù các slot đã lỡ. Phép trừ chịu millis wrap.
inline bool sampleDue(uint32_t now, uint32_t& scheduled, uint32_t period) {
  const uint32_t elapsed = now - scheduled;
  if (period == 0 || elapsed < period) return false;
  scheduled += (elapsed / period) * period;
  return true;
}

struct Moments {
  uint32_t count = 0;
  double mean = 0, m2 = 0;
  void add(double value) {
    ++count;
    const double delta = value - mean;
    mean += delta / count;
    m2 += delta * (value - mean);
  }
  double variance() const { return count > 1 ? m2 / (count - 1) : 0; }
};

// Chỉ là kiểm tra đứng yên kỹ thuật, không chứng minh gyro tuyệt đối không quay.
// Lấy offset một lần sau khi đủ mẫu ổn định; có timeout cứu hộ để không treo cảm biến.
class GyroBias {
 public:
  void reset() { *this = GyroBias(); }
  void restartWindow() { count_ = 0; axes_ = {}; acceleration_ = {}; hasTime_ = false; }
  bool update(uint64_t now, const std::array<float, 3>& a, const std::array<float, 3>& g) {
    if (ready_) return true;
    if (startTime_ == 0) startTime_ = now;
    const double an = std::sqrt(double(a[0])*a[0] + double(a[1])*a[1] + double(a[2])*a[2]);
    const double gn = std::sqrt(double(g[0])*g[0] + double(g[1])*g[1] + double(g[2])*g[2]);
    if (!std::isfinite(an) || !std::isfinite(gn) || std::fabs(an - 9.80665) > 1.2 || gn > 35) {
      restartWindow();
      if (now - startTime_ >= 3500) {
        for (size_t i = 0; i < 3; ++i) bias_[i] = static_cast<float>(axes_[i].count > 10 ? axes_[i].mean : 0.0);
        ready_ = true;
        return true;
      }
      return false;
    }
    if (hasTime_ && (now <= last_ || now - last_ > 100)) restartWindow();
    if (!hasTime_) { first_ = now; hasTime_ = true; }
    last_ = now;
    acceleration_.add(an);
    for (size_t i = 0; i < 3; ++i) axes_[i].add(g[i]);
    ++count_;
    if (count_ < 60 || now - first_ < 1200) {
      if (now - startTime_ >= 3500) {
        for (size_t i = 0; i < 3; ++i) bias_[i] = static_cast<float>(axes_[i].count > 10 ? axes_[i].mean : 0.0);
        ready_ = true;
        return true;
      }
      return false;
    }
    bool stable = acceleration_.variance() <= .25 * .25;
    for (const auto& axis : axes_) stable = stable && axis.variance() <= .35 * .35;
    if (!stable) {
      restartWindow();
      if (now - startTime_ >= 3500) {
        for (size_t i = 0; i < 3; ++i) bias_[i] = static_cast<float>(axes_[i].count > 10 ? axes_[i].mean : 0.0);
        ready_ = true;
        return true;
      }
      return false;
    }
    for (size_t i = 0; i < 3; ++i) bias_[i] = static_cast<float>(axes_[i].mean);
    ready_ = true;
    return true;
  }
  bool ready() const { return ready_; }
  const std::array<float, 3>& offsets() const { return bias_; }
 private:
  std::array<Moments, 3> axes_{};
  Moments acceleration_{};
  std::array<float, 3> bias_{};
  uint32_t count_ = 0;
  uint64_t first_ = 0, last_ = 0, startTime_ = 0;
  bool hasTime_ = false, ready_ = false;
};

// Baseline lấy từ mẫu điện áp trước EMA: không dùng độ mượt để chứng minh ổn định.
class VoltageBaseline {
 public:
  explicit VoltageBaseline(uint32_t windowMs = 5000) : windowMs_(windowMs) {}
  void reset() { *this = VoltageBaseline(windowMs_); }
  bool update(uint64_t now, double mv) {
    if (!std::isfinite(mv)) { reset(); return false; }
    if (ready_) return true;
    if (hasTime_ && (now <= last_ || now - last_ > 200)) reset();
    if (!hasTime_) { first_ = now; hasTime_ = true; }
    last_ = now;
    // Bỏ một giây đầu tiếp xúc trước khi lấy mức nền.
    if (now - first_ < 1000) return false;
    values_.add(mv);
    if (now - first_ < windowMs_ + 1000 || values_.count < 80) return false;
    // Ngưỡng kỹ thuật phát triển, phải đối chiếu trên module thật.
    if (values_.variance() > 50.0 * 50.0) { reset(); return false; }
    ready_ = true;
    return true;
  }
  bool ready() const { return ready_; }
  float millivolts() const { return static_cast<float>(values_.mean); }
 private:
  Moments values_{};
  uint64_t first_ = 0, last_ = 0;
  bool hasTime_ = false, ready_ = false;
  uint32_t windowMs_;
};

// Không suy ra µS từ một mô hình mạch chưa được hiệu chuẩn.
inline float gsrConductance(float volts, bool calibrated, float supply,
                            float offset, float resistorOhms) {
  if (!calibrated || !std::isfinite(volts) || !std::isfinite(supply) ||
      !std::isfinite(offset) || !std::isfinite(resistorOhms) || resistorOhms <= 0 ||
      volts <= offset || volts >= supply) return std::numeric_limits<float>::quiet_NaN();
  const float resistance = resistorOhms * (supply - volts) / (volts - offset);
  return resistance > 0 ? 1000000.0f / resistance : std::numeric_limits<float>::quiet_NaN();
}
}  // namespace asd

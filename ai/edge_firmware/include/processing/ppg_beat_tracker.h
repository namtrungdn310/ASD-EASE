#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <climits>

namespace asd {

// =============================================================================
// Thuật toán tách sóng PPG y sinh & Phát hiện nhịp tim chống đếm nhịp đôi:
// 1. Tách thành phần DC trượt (High-pass stage, alpha = 0.02) kèm xả quá độ bước nhảy DC
// 2. Bộ lọc thông thấp Butterworth bậc 2 (fc = 2.5 Hz @ fs = 50 Hz):
//    Triệt tiêu dicrotic notch (>3.5 Hz) và triệt tiêu rung giật vi cơ
// 3. Cửa sổ thời gian trơ sinh lý động (Adaptive Physiological Blanking Window):
//    Tuyệt đối không đếm sóng phản xạ tâm trương / dicrotic wave ở khoảng 300-350ms
// 4. Loại trừ sóng phản xạ harmonic (xấp xỉ 1/2 khoảng RR trước đó)
// 5. Lọc TRUNG VỊ (Median) trên mảng 8 nhịp gần nhất + EMA làm mượt
// 6. Chuẩn hóa chỉ số chất lượng tín hiệu (quality) trực tiếp từ độ ổn định mảng 8 nhịp
// =============================================================================
class PpgBeatTracker {
 public:
  struct Estimate {
    bool valid = false;
    float bpm = 0;
    float instantaneousBpm = 0;
    float peakToPeak = 0;
    float quality = 0;
    uint64_t measuredAtMs = 0;
    uint32_t intervalMs = 0;
    uint8_t acceptedIntervals = 0;
  };

  static constexpr float kMinimumBpm = 40.0f;
  static constexpr float kMaximumBpm = 200.0f;
  static constexpr size_t kRateBufferSize = 8;

  void reset() {
    *this = PpgBeatTracker{};
  }

  // Tính TRUNG VỊ (Median) từ mảng rates_[] chỉ lấy các slot hợp lệ (> 0)
  float computeMedianBpm() const {
    float tmp[kRateBufferSize];
    size_t n = 0;
    for (size_t i = 0; i < kRateBufferSize; ++i) {
      if (rates_[i] > 0.0f) tmp[n++] = rates_[i];
    }
    if (n == 0) return 0.0f;
    if (n == 1) return tmp[0];

    for (size_t i = 1; i < n; ++i) {
      float key = tmp[i];
      int j = static_cast<int>(i) - 1;
      while (j >= 0 && tmp[j] > key) {
        tmp[j + 1] = tmp[j];
        --j;
      }
      tmp[j + 1] = key;
    }

    if (n % 2 == 1) {
      return tmp[n / 2];
    } else {
      return (tmp[n / 2 - 1] + tmp[n / 2]) * 0.5f;
    }
  }

  // Chuẩn hóa chất lượng tín hiệu HR [0.0 .. 1.0] đồng bộ trực tiếp với thuật toán đã chốt:
  // Kết hợp độ đầy cửa sổ 8 nhịp, độ tập trung quanh Trung vị (Median) và biên độ Vpp.
  float computeBeatQuality(float vpp) const {
    if (validBeatCount_ == 0) {
      return (vpp >= 20.0f) ? 0.20f : 0.05f;
    }
    if (validBeatCount_ == 1 || medianBpm_ <= 0.0f) {
      return (vpp >= 20.0f) ? 0.35f : 0.15f;
    }

    float madSum = 0.0f;
    size_t n = 0;
    for (size_t i = 0; i < kRateBufferSize; ++i) {
      if (rates_[i] > 0.0f) {
        madSum += std::fabs(rates_[i] - medianBpm_) / medianBpm_;
        ++n;
      }
    }
    const float madRatio = (n > 0) ? (madSum / static_cast<float>(n)) : 0.0f;
    const float stability = std::max(0.60f, 1.0f - madRatio * 1.50f);
    const float maturity = std::min(1.0f, 0.54f + 0.08f * static_cast<float>(std::min<size_t>(validBeatCount_, 6)));
    const float ampNorm = std::max(0.0f, std::min(1.0f, (vpp - 20.0f) / 80.0f));
    const float ampFactor = 0.78f + 0.22f * ampNorm;

    return std::max(0.55f, std::min(1.0f, maturity * stability * ampFactor));
  }

  const Estimate& update(uint32_t ir, uint64_t measuredAtMs) {
    if (hasTime_ && (measuredAtMs <= lastSampleAtMs_ || measuredAtMs - lastSampleAtMs_ > 500)) {
      reset();
    }
    lastSampleAtMs_ = measuredAtMs;
    hasTime_ = true;

    const float x = static_cast<float>(ir);

    // 1. Tách thành phần DC cho kênh IR (kèm xả quá độ khi bước nhảy DC lớn > 6000 counts)
    if (irDc_ == 0.0f) {
      irDc_ = x;
    } else if (std::fabs(x - irDc_) > 6000.0f) {
      irDc_ = x;
      biquadX1_ = biquadX2_ = biquadY1_ = biquadY2_ = 0.0f;
      acFiltered_ = prevAc_ = prev2Ac_ = 0.0f;
      acMax_ = acMin_ = 0.0f;
    } else {
      irDc_ = irDc_ * 0.98f + x * 0.02f;
    }
    const float ac = x - irDc_;

    // 2. Bộ lọc thông thấp Butterworth bậc 2 (fc = 2.5 Hz @ fs = 50 Hz)
    static constexpr float kB0 =  0.020083f;
    static constexpr float kB1 =  0.040167f;
    static constexpr float kB2 =  0.020083f;
    static constexpr float kA1 = -1.561018f;
    static constexpr float kA2 =  0.641351f;

    const float acF = kB0 * ac + kB1 * biquadX1_ + kB2 * biquadX2_
                    - kA1 * biquadY1_ - kA2 * biquadY2_;
    biquadX2_ = biquadX1_;
    biquadX1_ = ac;
    biquadY2_ = biquadY1_;
    biquadY1_ = acF;
    acFiltered_ = acF;

    // 3. Theo dõi biên độ đỉnh-đáy thích ứng
    if (acFiltered_ > acMax_) {
      acMax_ = acFiltered_;
    } else {
      acMax_ -= (acMax_ - 0.0f) * 0.006f;
    }

    if (acFiltered_ < acMin_) {
      acMin_ = acFiltered_;
    } else {
      acMin_ += (0.0f - acMin_) * 0.006f;
    }

    const float vpp = acMax_ - acMin_;

    // 4. Bắt đỉnh sóng mạch tâm thu (Systolic Peak Detection)
    const bool isPeak = (prevAc_ > prev2Ac_) && (prevAc_ >= acFiltered_);
    const float threshold = acMin_ + vpp * 0.60f;

    // 5. Kiểm tra điều kiện bắt nhịp
    if (isPeak && (prevAc_ > threshold) && (vpp >= 20.0f)) {
      if (lastBeatMs_ > 0) {
        const uint64_t delta = measuredAtMs - lastBeatMs_;

        // Thời gian trơ sinh lý động (Adaptive Physiological Blanking Window):
        // Với nhịp nghỉ (60-110 bpm -> RR 545-1000ms), 0.60*RR = 327-600ms vẫn chặn hoàn toàn dicrotic notch,
        // đồng thời sàn 280ms cho phép đo chính xác toàn dải khai báo 40..200 bpm (300ms @ 200 bpm).
        uint64_t blankingWindow = 280;
        if (lastRrIntervalMs_ > 0) {
          blankingWindow = static_cast<uint64_t>(lastRrIntervalMs_ * 0.60f);
          if (blankingWindow < 280) blankingWindow = 280;
          if (blankingWindow > 650) blankingWindow = 650;
        }

        // Theo dõi chuỗi đỉnh đều đặn liên tiếp (trên mọi đỉnh vật lý) để phát hiện bước nhảy nhịp thực
        // (vd 60 -> 120 bpm cho chuỗi 500, 500, 500, 500ms), phân biệt hẳn với dicrotic notch (luân phiên ngắn-dài).
        bool unlockedFastStep = false;
        if (lastRrIntervalMs_ > 0 && lastCandidatePeakMs_ > 0 && measuredAtMs > lastCandidatePeakMs_) {
          const uint64_t peakDelta = measuredAtMs - lastCandidatePeakMs_;
          const bool fasterThanCurrent = peakDelta >= 280 && peakDelta <= 750 &&
                                         (peakDelta * 10ULL < lastRrIntervalMs_ * 7ULL);
          if (fasterThanCurrent) {
            if (lastCandidateDeltaMs_ > 0 &&
                std::labs(static_cast<long>(peakDelta) - static_cast<long>(lastCandidateDeltaMs_)) <= 70) {
              ++fastCandidateCount_;
            } else {
              fastCandidateCount_ = 1;
            }
            lastCandidateDeltaMs_ = peakDelta;
            if (fastCandidateCount_ >= 4) {
              unlockedFastStep = true;
            }
          } else {
            fastCandidateCount_ = 0;
            lastCandidateDeltaMs_ = 0;
          }
        }
        lastCandidatePeakMs_ = measuredAtMs;

        bool acceptBeat = (delta >= blankingWindow && delta <= 1800);
        if (acceptBeat) {
          // Kiểm tra loại trừ sóng phản xạ harmonic (xấp xỉ 1/2 khoảng RR trước đó)
          if (lastRrIntervalMs_ > 0 && validBeatCount_ >= 2) {
            long halfRr = static_cast<long>(lastRrIntervalMs_ / 2);
            if (std::labs(static_cast<long>(delta) - halfRr) < 70) {
              acceptBeat = false;
            }
          }
        }

        if (unlockedFastStep && lastCandidateDeltaMs_ >= 280) {
          const float stepBpm = 60000.0f / static_cast<float>(lastCandidateDeltaMs_);
          if (stepBpm >= kMinimumBpm && stepBpm <= kMaximumBpm) {
            rates_.fill(0.0f);
            rates_[0] = stepBpm;
            rateSpot_ = 1;
            lastRrIntervalMs_ = lastCandidateDeltaMs_;
            lastBeatMs_ = measuredAtMs;
            validBeatCount_ = std::max<size_t>(validBeatCount_, 2);
            medianBpm_ = stepBpm;
            smoothedBpm_ = stepBpm;
            emaInitialized_ = true;
            fastCandidateCount_ = 0;
            lastCandidateDeltaMs_ = 0;
            result_.valid = true;
            result_.bpm = smoothedBpm_;
            result_.instantaneousBpm = stepBpm;
            result_.intervalMs = static_cast<uint32_t>(lastRrIntervalMs_);
            result_.measuredAtMs = measuredAtMs;
            result_.peakToPeak = vpp;
            result_.acceptedIntervals = static_cast<uint8_t>(std::min<size_t>(validBeatCount_, 255));
          }
        } else if (acceptBeat) {
          const float instantBpm = 60000.0f / static_cast<float>(delta);
          if (instantBpm >= kMinimumBpm && instantBpm <= kMaximumBpm) {
            rates_[rateSpot_++] = instantBpm;
            rateSpot_ %= kRateBufferSize;

            lastRrIntervalMs_ = delta;
            lastBeatMs_       = measuredAtMs;
            validBeatCount_++;

            // Tính TRUNG VỊ khoảng RR (loại bỏ nhịp bất thường)
            medianBpm_ = computeMedianBpm();

            // EMA nhẹ trên TRUNG VỊ (làm mượt hiển thị)
            if (!emaInitialized_) {
              smoothedBpm_ = medianBpm_;
              emaInitialized_ = true;
            } else {
              smoothedBpm_ = 0.30f * medianBpm_ + 0.70f * smoothedBpm_;
            }

            result_.valid = validBeatCount_ >= 2;
            result_.bpm = smoothedBpm_;
            result_.instantaneousBpm = instantBpm;
            result_.intervalMs = static_cast<uint32_t>(delta);
            result_.measuredAtMs = measuredAtMs;
            result_.peakToPeak = vpp;
            result_.acceptedIntervals = static_cast<uint8_t>(std::min<size_t>(validBeatCount_, 255));
          }
        } else if (delta > 1800) {
          lastBeatMs_ = measuredAtMs;
          lastRrIntervalMs_ = 0;
          fastCandidateCount_ = 0;
          lastCandidateDeltaMs_ = 0;
        }
      } else {
        lastBeatMs_ = measuredAtMs;
      }
    }

    // Cập nhật lịch sử đỉnh
    prev2Ac_ = prevAc_;
    prevAc_  = acFiltered_;

    // Quá 3500ms không có nhịp mới thì reset nhịp trung bình và bộ lọc
    if (lastBeatMs_ > 0 && (measuredAtMs - lastBeatMs_ > 3500)) {
      medianBpm_        = 0.0f;
      smoothedBpm_      = 0.0f;
      lastRrIntervalMs_ = 0;
      validBeatCount_   = 0;
      rateSpot_         = 0;
      rates_.fill(0.0f);
      emaInitialized_   = false;
      result_           = {};
    }

    // Giữ timestamp hợp lệ trong lúc cổ tay vẫn tiếp xúc để dashboard vẽ nét liền ổn định giữa 2 nhịp
    if (result_.valid && measuredAtMs - lastBeatMs_ <= 2500) {
      result_.measuredAtMs = measuredAtMs;
    }

    result_.peakToPeak = vpp;
    result_.quality = computeBeatQuality(vpp);
    return result_;
  }

  const Estimate& estimate() const { return result_; }

 private:
  Estimate result_{};
  std::array<float, kRateBufferSize> rates_{};

  float irDc_ = 0.0f;
  float biquadX1_ = 0.0f;
  float biquadX2_ = 0.0f;
  float biquadY1_ = 0.0f;
  float biquadY2_ = 0.0f;
  float acFiltered_ = 0.0f;
  float prevAc_ = 0.0f;
  float prev2Ac_ = 0.0f;
  uint64_t lastCandidatePeakMs_ = 0;
  uint64_t lastCandidateDeltaMs_ = 0;
  uint8_t fastCandidateCount_ = 0;
  float acMax_ = 0.0f;
  float acMin_ = 0.0f;

  uint64_t lastSampleAtMs_ = 0;
  uint64_t lastBeatMs_ = 0;
  uint64_t lastRrIntervalMs_ = 0;
  size_t rateSpot_ = 0;
  size_t validBeatCount_ = 0;

  float medianBpm_ = 0.0f;
  float smoothedBpm_ = 0.0f;
  bool emaInitialized_ = false;
  bool hasTime_ = false;
};

}  // namespace asd

#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

#include "GSRSensor.h"
#include "MAX30102Sensor.h"
#include "MPU6050Sensor.h"
#include "model_config.h"
#include "model_generated.h"

namespace asd {

// =============================================================================
// Bộ trích xuất 36 đặc trưng đa cảm biến (EDA, ACC, HR) & Suy luận TinyML
// trên ESP32-S3 đồng bộ trực tiếp với model_generated.h (wesad_lr_v1_folded).
// Nâng cấp Bước 1:
// - (1) Chuẩn hóa EDA quanh nền cá nhân (giảm báo giả cho người mồ hôi tay nhiều).
// - (2) Cổng bảo vệ tay tĩnh khi ngồi học (không cho tay yên tĩnh tự kích Stress).
// - (3) Trọng số thống kê HR: mẫu chuẩn nét xanh w=1.0, mẫu duy trì nét vàng w=0.25.
// - (4) Phối hợp HrStabilityFilter lọc bỏ gai nhảy vọt/tụt sâu trước khi vào hrBuf_.
// - (5) Tách đập bàn 1 lần (lọc bỏ xung nhiễu) vs đập >= 3 lần/30s (tăng cảnh báo).
// =============================================================================
class EdgeAiInference {
 public:
  struct Result {
    bool available = EDGE_MODEL_AVAILABLE;
    bool hasProbability = false;
    float probability = -1.0f;
    float logit = 0.0f;
    uint8_t windowSeconds = 0;
    const char* state = "UNCERTAIN";
    const char* modelVersion = EDGE_MODEL_AVAILABLE ? MODEL_VERSION : "none";
    float rawProbability = -1.0f;
    float edaBaselineUs = 1.9574f;
    float restingHrBpm = 75.0f;
    float rmssdMs = -1.0f;
    float restingRmssdMs = -1.0f;
    float gyroRms = 0.0f;
    float vasoRatio = 1.0f;
    bool quietHandGuarded = false;
    bool repeatedImpactTriggered = false;
    uint8_t impacts30s = 0;
  };

  void reset() {
    // Tuyệt đối không dùng `*this = EdgeAiInference{}` trên ESP32 vì EdgeAiInference > 14 KB,
    // sẽ gây tràn stack 8 KB của loopTask và làm chip panic/reboot mất kết nối vài giây.
    resetWindow();
    edaBuf_.fill(0.0f);
    accX_.fill(0.0f);
    accY_.fill(0.0f);
    accZ_.fill(0.0f);
    accNorm_.fill(0.0f);
    hrBuf_.fill(0.0f);
    impacts30s_ = 0;
    adcFast_ = 0.0f;
    adcSlow_ = 0.0f;
    lastEdaUs_ = kWesadNeutralEdaUs;
    waitForFreshHrAfterDrop_ = false;
    result_ = Result{};
  }

  const Result& update(uint64_t nowMs, const MAX30102Data& ppg,
                       const MPU6050Data& imu, const GSRData& gsr,
                       bool suppressSingleImpact = false,
                       uint8_t impacts30s = 0) {
    if (!EDGE_MODEL_AVAILABLE) {
      result_.available = false;
      result_.hasProbability = false;
      result_.probability = -1.0f;
      result_.windowSeconds = 0;
      result_.state = "UNCERTAIN";
      result_.modelVersion = "none";
      return result_;
    }

    result_.available = true;
    result_.modelVersion = MODEL_VERSION;
    impacts30s_ = impacts30s;
    result_.impacts30s = impacts30s;

    // 1. Nếu chưa đeo vào cổ tay (!fingerDetected):
    //    - Nếu chưa từng bắt đầu phiên đeo ổn định nào -> lập tức trả UNCERTAIN (không trả NORMAL 5s đầu).
    //    - Nếu đang có phiên đeo trước đó và hở tay thoáng qua < 5.2s -> giữ bộ đệm 60s
    //      để UI hiển thị đếm ngược ân hạn 5s; quá 5.2s thì xóa sạch về UNCERTAIN.
    const bool hasWristContact =
        ppg.fingerDetected || ((hasStartedWithHr_ || hasCompletedCalibration_) && ppg.exposureSettling);
    if (!hasWristContact) {
      waitForFreshHrAfterDrop_ = false;
      if (!hasStartedWithHr_ && !hasCompletedCalibration_) {
        resetWindow();
        result_.hasProbability = false;
        result_.probability = -1.0f;
        result_.rawProbability = -1.0f;
        result_.logit = 0.0f;
        result_.windowSeconds = 0;
        result_.quietHandGuarded = false;
        result_.repeatedImpactTriggered = false;
        result_.state = "UNCERTAIN";
        return result_;
      }

      if (noContactSinceMs_ == 0) {
        noContactSinceMs_ = nowMs;
      }
      const uint64_t noContactElapsed = (nowMs >= noContactSinceMs_) ? (nowMs - noContactSinceMs_) : 0;
      if (noContactElapsed >= kNoContactResetGraceMs) {
        resetWindow();
        result_.hasProbability = false;
        result_.probability = -1.0f;
        result_.rawProbability = -1.0f;
        result_.logit = 0.0f;
        result_.windowSeconds = 0;
        result_.quietHandGuarded = false;
        result_.repeatedImpactTriggered = false;
        result_.state = "UNCERTAIN";
        return result_;
      }

      result_.windowSeconds = static_cast<uint8_t>(hrCount_);
      const bool isCalibrating = hasStartedWithHr_ && !hasCompletedCalibration_;
      if (isCalibrating) {
        result_.hasProbability = false;
        result_.probability = -1.0f;
        result_.rawProbability = -1.0f;
        result_.logit = 0.0f;
        result_.state = "CALIBRATING";
      } else {
        // Đang trong 5.2s ân hạn khi đã có kết quả NORMAL/ATTENTION: giữ nguyên trạng thái & xác suất gần nhất
        result_.state = inAttentionState_ ? "ATTENTION" : "NORMAL";
      }
      return result_;
    }

    if (noContactSinceMs_ != 0) {
      const uint64_t pauseDurationMs = (nowMs >= noContactSinceMs_) ? (nowMs - noContactSinceMs_) : 0;
      if (lastEdaSampleMs_ > 0) lastEdaSampleMs_ += pauseDurationMs;
      if (lastAccSampleMs_ > 0) lastAccSampleMs_ += pauseDurationMs;
      if (lastHrSampleMs_ > 0)  lastHrSampleMs_  += pauseDurationMs;
      noContactSinceMs_ = 0;
    }

    // 2. Kiểm tra hiệu lực nhịp tim trên cổ tay (xung mới <= 3s, duy trì <= 15s)
    const bool hasHrTimestamp = ppg.heartRateMonotonicMs > 0 && nowMs >= ppg.heartRateMonotonicMs;
    const uint64_t hrAgeMs = hasHrTimestamp ? (nowMs - ppg.heartRateMonotonicMs) : UINT64_MAX;
    const bool hasFreshHr  = hasHrTimestamp &&
                             ppg.hasHeartRateTimestamp &&
                             std::isfinite(ppg.heartRate) &&
                             ppg.heartRate >= 40.0f &&
                             ppg.heartRate <= 200.0f &&
                             (hrAgeMs <= kFreshHrMaxAgeMs);
    const bool hasActiveHr = hasHrTimestamp && (hrAgeMs <= kActiveHrMaxAgeMs);

    // Chỉ bắt đầu hiệu chuẩn 60s khi tiếp xúc cổ tay đã ổn định (contactSettled) hoặc có nhịp tim thực.
    // Nếu vừa rớt khỏi NORMAL/ATTENTION vì mất xung HR quá 15s + 5.2s (vd đặt úp lên mặt bàn phản xạ IR),
    // giữ nguyên UNCERTAIN cho tới khi có xung nhịp tim thực mới (hasFreshHr) hoặc nhấc vòng khỏi mặt bàn.
    if (!hasStartedWithHr_ && !hasCompletedCalibration_ &&
        ((waitForFreshHrAfterDrop_ && !hasFreshHr) || (!ppg.contactSettled && !hasFreshHr))) {
      result_.hasProbability = false;
      result_.probability = -1.0f;
      result_.rawProbability = -1.0f;
      result_.logit = 0.0f;
      result_.windowSeconds = 0;
      result_.quietHandGuarded = false;
      result_.repeatedImpactTriggered = false;
      result_.state = "UNCERTAIN";
      return result_;
    }

    if (hasFreshHr) {
      waitForFreshHrAfterDrop_ = false;
    }
    hasStartedWithHr_ = true;

    // 3. Thu mẫu EDA ở tần số 4 Hz (mỗi 250 ms)
    if (lastEdaSampleMs_ == 0 || nowMs - lastEdaSampleMs_ >= 250) {
      lastEdaSampleMs_ = nowMs;
      sampleEda(gsr);
    }

    // 4. Thu mẫu Gia tốc 3 trục ở tần số 10 Hz (mỗi 100 ms)
    if (lastAccSampleMs_ == 0 || nowMs - lastAccSampleMs_ >= 100) {
      lastAccSampleMs_ = nowMs;
      sampleAcc(imu, suppressSingleImpact);
    }

    // 5. Thu mẫu Nhịp tim ở tần số 1 Hz (mỗi 1000 ms) & suy luận theo bước trượt 10 giây
    if (lastHrSampleMs_ == 0 || nowMs - lastHrSampleMs_ >= 1000) {
      lastHrSampleMs_ = nowMs;
      sampleHr(ppg, hasFreshHr);
      ++hrSamplesSinceLastStep_;
      result_.windowSeconds = static_cast<uint8_t>(hrCount_);

      const bool sensorsCalibrating = (imu.status == IMUStatus::CALIBRATING) ||
                                      (gsr.status == GSRStatus::CALIBRATING);
      const bool windowFull = (edaCount_ >= kMaxEdaSamples) &&
                              (accCount_ >= kMaxAccSamples) &&
                              (hrCount_ >= kMaxHrSamples);

      if (sensorsCalibrating || !windowFull || !hasActiveHr) {
        if (hasCompletedCalibration_ && windowFull) {
          if (recalibGraceSinceMs_ == 0) {
            recalibGraceSinceMs_ = nowMs;
          }
          const uint64_t graceElapsed = (nowMs >= recalibGraceSinceMs_) ? (nowMs - recalibGraceSinceMs_) : 0;
          if (graceElapsed < kNoContactResetGraceMs) {
            // Giữ nguyên trạng thái & xác suất trong 5.2s ân hạn tránh nhấp nháy UI
            result_.state = inAttentionState_ ? "ATTENTION" : "NORMAL";
            hrSamplesSinceLastStep_ = kStepHrSamples;
            return result_;
          }
          // Hết 5.2s ân hạn khi mất xung HR quá 15s (hoặc đặt vòng lên mặt bàn): xóa sạch cửa sổ về UNCERTAIN
          // và chờ nhịp tim thực mới trước khi hiệu chuẩn lại 60s.
          resetWindow();
          if (!hasActiveHr) {
            waitForFreshHrAfterDrop_ = true;
            result_.hasProbability = false;
            result_.probability = -1.0f;
            result_.rawProbability = -1.0f;
            result_.logit = 0.0f;
            result_.windowSeconds = 0;
            result_.quietHandGuarded = false;
            result_.repeatedImpactTriggered = false;
            result_.state = "UNCERTAIN";
            hrSamplesSinceLastStep_ = kStepHrSamples;
            return result_;
          }
          hasStartedWithHr_ = true;
          result_.windowSeconds = 0;
        }
        recalibGraceSinceMs_ = 0;
        result_.hasProbability = false;
        result_.probability = -1.0f;
        result_.rawProbability = -1.0f;
        result_.quietHandGuarded = false;
        result_.repeatedImpactTriggered = false;
        result_.state = "CALIBRATING";
        hrSamplesSinceLastStep_ = kStepHrSamples;
      } else {
        recalibGraceSinceMs_ = 0;
        if (!result_.hasProbability || hrSamplesSinceLastStep_ >= kStepHrSamples) {
          runInference();
        }
      }
    }

    return result_;
  }

  const Result& latest() const { return result_; }

 private:
  static constexpr size_t kMaxEdaSamples = 240;  // 60s @ 4 Hz
  static constexpr size_t kMaxAccSamples = 600;  // 60s @ 10 Hz
  static constexpr size_t kMaxHrSamples  = 60;   // 60s @ 1 Hz
  static constexpr size_t kStepHrSamples = 10;   // Bước trượt 10s @ 1 Hz
  static constexpr uint64_t kFreshHrMaxAgeMs  = 3000ULL;
  static constexpr uint64_t kActiveHrMaxAgeMs = 15000ULL;
  static constexpr uint64_t kNoContactResetGraceMs = 5200ULL;
  static constexpr float kAttentionEnterThreshold = 0.70f;
  static constexpr float kAttentionExitThreshold  = 0.55f;
  static constexpr float kWesadNeutralEdaUs = 1.9574f;
  static constexpr float kGreenHrWeight = 1.0f;
  static constexpr float kYellowHrWeight = 0.25f;
  static constexpr float kAdcNoiseDeadband = 6.0f;

  void resetWindow() {
    edaHead_ = edaCount_ = 0;
    accHead_ = accCount_ = 0;
    hrHead_  = hrCount_  = 0;
    hrSamplesSinceLastStep_ = 0;
    lastEdaSampleMs_ = 0;
    lastAccSampleMs_ = 0;
    lastHrSampleMs_  = 0;
    noContactSinceMs_ = 0;
    recalibGraceSinceMs_ = 0;
    hasStartedWithHr_ = false;
    hasCompletedCalibration_ = false;
    inAttentionState_ = false;
    edaBaselineInitialized_ = false;
    edaBaselineSum_ = 0.0f;
    edaBaselineSamples_ = 0;
    edaBaselineUs_ = kWesadNeutralEdaUs;
    adcBaselineInitialized_ = false;
    adcBaselineSum_ = 0.0f;
    adcBaselineSamples_ = 0;
    adcBaselineRaw_ = 1800.0f;
    lastAcceptedAdc_ = 0.0f;
    restingHrCount_ = 0;
    restingHrSum_ = 0.0f;
    restingHrBpm_ = 75.0f;
    latestHrForBaseline_ = 75.0f;
    hasLatestHrForBaseline_ = false;
    restingRmssdInitialized_ = false;
    restingRmssdSum_ = 0.0f;
    restingRmssdCount_ = 0;
    restingRmssdMs_ = -1.0f;
    restingPpgAmpInitialized_ = false;
    restingPpgAmpSum_ = 0.0f;
    restingPpgAmpCount_ = 0;
    restingPpgAmp_ = 0.0f;
    gyroNorm_.fill(0.0f);
    gyroValidBuf_.fill(false);
    rrBuf_.fill(NAN);
    ampBuf_.fill(NAN);
    adcInitialized_ = false;
    result_.rmssdMs = -1.0f;
    result_.restingRmssdMs = -1.0f;
    result_.gyroRms = 0.0f;
    result_.vasoRatio = 1.0f;
  }

  void sampleEda(const GSRData& gsr) {
    const bool readable = (gsr.status == GSRStatus::VALID || gsr.status == GSRStatus::CALIBRATING) &&
                          gsr.rawADC > 0 && gsr.rawADC < 4095;
    float edaUs = kWesadNeutralEdaUs;
    const bool calmHrForBaseline = !hasLatestHrForBaseline_ || (latestHrForBaseline_ <= restingHrBpm_ + 4.5f);
    if (readable) {
      const float rawAdc = static_cast<float>(gsr.rawADC);
      float adc = rawAdc;
      if (!adcInitialized_) {
        adcFast_ = adcSlow_ = lastAcceptedAdc_ = adc;
        adcInitialized_ = true;
      } else {
        // Vùng chết ±6 ADC chặn nhiễu lượng tử khi da ổn định
        if (std::fabs(rawAdc - lastAcceptedAdc_) < kAdcNoiseDeadband) {
          adc = lastAcceptedAdc_;
        } else {
          lastAcceptedAdc_ = rawAdc;
        }
        adcFast_ = 0.25f * adc + 0.75f * adcFast_;
        adcSlow_ = 0.005f * adc + 0.995f * adcSlow_;
      }

      // Chuẩn hóa EDA theo biến thiên tương đối quanh nền cá nhân (giảm sai lệch do cơ địa mồ hôi tay nhiều)
      if (gsr.conductanceCalibrated && std::isfinite(gsr.conductance_uS) && gsr.conductance_uS > 0.05f) {
        const float rawUs = std::max(0.20f, std::min(25.0f, gsr.conductance_uS));
        if (gsr.status == GSRStatus::VALID) {
          if (!edaBaselineInitialized_) {
            edaBaselineSum_ += rawUs;
            ++edaBaselineSamples_;
            edaBaselineUs_ = edaBaselineSum_ / static_cast<float>(edaBaselineSamples_);
            if (edaBaselineSamples_ >= 20) {
              edaBaselineInitialized_ = true;
            }
          } else if (!inAttentionState_ && impacts30s_ == 0 && calmHrForBaseline &&
                     std::fabs(rawUs - edaBaselineUs_) <= 0.35f * std::max(0.50f, edaBaselineUs_)) {
            // Trượt nền cực chậm theo trôi nhiệt chỉ khi HR đang ở vùng nghỉ ngơi
            edaBaselineUs_ = 0.9985f * edaBaselineUs_ + 0.0015f * rawUs;
          }
          const float relRatio = (rawUs - edaBaselineUs_) / std::max(0.50f, edaBaselineUs_);
          edaUs = std::max(0.20f, std::min(15.0f, kWesadNeutralEdaUs + relRatio * 2.5f));
        } else {
          edaUs = kWesadNeutralEdaUs;
        }
      } else {
        // Khi chưa hiệu chuẩn µS (Grove GSR ADC thô): đo độ lệch tương đối quanh nền ADC cá nhân
        // để cả chiều ADC tăng (vd 1550->2250) hay giảm đều phản ánh đúng cường độ thay đổi.
        if (gsr.status == GSRStatus::VALID) {
          if (!adcBaselineInitialized_) {
            adcBaselineSum_ += adc;
            ++adcBaselineSamples_;
            adcBaselineRaw_ = adcBaselineSum_ / static_cast<float>(adcBaselineSamples_);
            if (adcBaselineSamples_ >= 20) {
              adcBaselineInitialized_ = true;
            }
          } else if (!inAttentionState_ && impacts30s_ == 0 && calmHrForBaseline &&
                     std::fabs(adc - adcBaselineRaw_) <= 0.22f * std::max(150.0f, adcBaselineRaw_)) {
            adcBaselineRaw_ = 0.9985f * adcBaselineRaw_ + 0.0015f * adc;
          }
        }
        const float normBase = std::max(150.0f, adcBaselineInitialized_ ? adcBaselineRaw_ : adcSlow_);
        const float relAdcShift = std::fabs(adcFast_ - normBase) / normBase;
        const float tonicShift = std::min(2.20f, relAdcShift * 3.2f);
        const float phasicJitter = std::min(1.50f, (std::fabs(adc - adcFast_) / normBase) * 4.0f);
        edaUs = std::max(0.20f, std::min(15.0f, kWesadNeutralEdaUs + tonicShift + phasicJitter));
      }
    } else if (adcInitialized_) {
      edaUs = lastEdaUs_;
    }

    lastEdaUs_ = edaUs;
    edaBuf_[edaHead_] = edaUs;
    edaHead_ = (edaHead_ + 1) % kMaxEdaSamples;
    if (edaCount_ < kMaxEdaSamples) ++edaCount_;
  }

  void sampleAcc(const MPU6050Data& imu, bool suppressSingleImpact) {
    float ax = 0.0f, ay = 0.0f, az = 9.80665f;
    float gyroMag = 0.0f;
    bool gyroValid = false;
    if (suppressSingleImpact && accCount_ > 0) {
      // Lọc bỏ xung va chạm đơn lẻ 1 lần để không làm méo phương sai 60s
      const size_t prev = (accHead_ + kMaxAccSamples - 1) % kMaxAccSamples;
      ax = accX_[prev];
      ay = accY_[prev];
      az = accZ_[prev];
      gyroMag = gyroNorm_[prev];
      gyroValid = gyroValidBuf_[prev];
    } else if (imu.valid && imu.status == IMUStatus::VALID &&
               std::isfinite(imu.ax) && std::isfinite(imu.ay) && std::isfinite(imu.az)) {
      ax = imu.ax;
      ay = imu.ay;
      az = imu.az;
      if (imu.gyroCalibrated && std::isfinite(imu.gx_deg) && std::isfinite(imu.gy_deg) &&
          std::isfinite(imu.gz_deg)) {
        gyroMag = std::sqrt(imu.gx_deg * imu.gx_deg + imu.gy_deg * imu.gy_deg +
                            imu.gz_deg * imu.gz_deg);
        gyroValid = true;
      }
    } else if (accCount_ > 0) {
      const size_t prev = (accHead_ + kMaxAccSamples - 1) % kMaxAccSamples;
      ax = accX_[prev];
      ay = accY_[prev];
      az = accZ_[prev];
      gyroMag = gyroNorm_[prev];
      gyroValid = gyroValidBuf_[prev];
    }
    const float norm = std::sqrt(ax * ax + ay * ay + az * az);
    accX_[accHead_] = ax;
    accY_[accHead_] = ay;
    accZ_[accHead_] = az;
    accNorm_[accHead_] = norm;
    gyroNorm_[accHead_] = gyroMag;
    gyroValidBuf_[accHead_] = gyroValid;
    accHead_ = (accHead_ + 1) % kMaxAccSamples;
    if (accCount_ < kMaxAccSamples) ++accCount_;
  }

  void sampleHr(const MAX30102Data& ppg, bool hasFreshHr) {
    float hr = NAN;
    float rrMs = NAN;
    float ppgAmp = NAN;
    if (hasFreshHr) {
      hr = ppg.heartRate;
      latestHrForBaseline_ = hr;
      hasLatestHrForBaseline_ = true;
      if (ppg.beatIntervalMs >= 300 && ppg.beatIntervalMs <= 1500) {
        rrMs = static_cast<float>(ppg.beatIntervalMs);
      }
      if (std::isfinite(ppg.beatPeakToPeak) && ppg.beatPeakToPeak > 1.0f) {
        ppgAmp = ppg.beatPeakToPeak;
      }
      if (restingHrCount_ < 5) {
        restingHrSum_ += hr;
        ++restingHrCount_;
        restingHrBpm_ = restingHrSum_ / static_cast<float>(restingHrCount_);
      } else if (!inAttentionState_ && hr <= restingHrBpm_ + 4.0f) {
        restingHrBpm_ = 0.995f * restingHrBpm_ + 0.005f * hr;
      }
    }
    hrBuf_[hrHead_] = hr;
    rrBuf_[hrHead_] = rrMs;
    ampBuf_[hrHead_] = ppgAmp;
    hrHead_ = (hrHead_ + 1) % kMaxHrSamples;
    if (hrCount_ < kMaxHrSamples) ++hrCount_;
  }

  void runInference() {
    float features[MODEL_FEATURE_COUNT] = {};
    extractEdaFeatures(features);
    extractAccFeatures(features);
    extractHrFeatures(features);

    // Đảm bảo cửa sổ 60s có ít nhất 30% mẫu nhịp tim hợp lệ (hr_is_valid == 1.0)
    if (features[29] < 0.5f) {
      result_.hasProbability = false;
      result_.probability = -1.0f;
      result_.rawProbability = -1.0f;
      result_.state = "CALIBRATING";
      return;
    }

    const float logit = edge_compute_logit(features);
    const float rawProb = edge_predict_stress_probability(features);
    if (!std::isfinite(rawProb)) {
      result_.hasProbability = false;
      result_.probability = -1.0f;
      result_.rawProbability = -1.0f;
      result_.state = "UNCERTAIN";
      return;
    }

    hrSamplesSinceLastStep_ = 0;

    // Đọc các kênh bổ sung: Gyroscope (góc quay), HRV (RMSSD) & co mạch PPG
    const float gyroRms = extractGyroRms();
    float rmssdMs = -1.0f;
    float ampMean = -1.0f;
    const bool hrvValid = extractHrvRmssd(rmssdMs);
    const bool ampValid = extractPpgAmplitude(ampMean);

    const float edaMean = features[0];
    const float edaSlope = features[5];
    const float edaPhasicMean = features[8];
    const float edaScrCount = features[12];
    const float accNormStd = features[15];
    const float hrMean = features[30];
    const float hrMax = features[33];
    const float hrSlope = features[35];

    if (hrvValid && rmssdMs >= 5.0f && !inAttentionState_ &&
        hrMean <= restingHrBpm_ + 4.5f && impacts30s_ == 0) {
      if (!restingRmssdInitialized_) {
        restingRmssdSum_ += rmssdMs;
        ++restingRmssdCount_;
        restingRmssdMs_ = restingRmssdSum_ / static_cast<float>(restingRmssdCount_);
        if (restingRmssdCount_ >= 3) {
          restingRmssdInitialized_ = true;
        }
      } else {
        restingRmssdMs_ = 0.95f * restingRmssdMs_ + 0.05f * rmssdMs;
      }
    }

    if (ampValid && !inAttentionState_ &&
        hrMean <= restingHrBpm_ + 4.5f && impacts30s_ == 0) {
      if (!restingPpgAmpInitialized_) {
        restingPpgAmpSum_ += ampMean;
        ++restingPpgAmpCount_;
        restingPpgAmp_ = restingPpgAmpSum_ / static_cast<float>(restingPpgAmpCount_);
        if (restingPpgAmpCount_ >= 3) {
          restingPpgAmpInitialized_ = true;
        }
      } else {
        restingPpgAmp_ = 0.95f * restingPpgAmp_ + 0.05f * ampMean;
      }
    }

    const float hrvDropNorm =
        (hrvValid && restingRmssdInitialized_ && restingRmssdMs_ >= 12.0f)
            ? std::max(0.0f, std::min(1.0f, (0.90f - (rmssdMs / restingRmssdMs_)) / 0.45f))
            : 0.0f;
    const float vasoRatio =
        (ampValid && restingPpgAmpInitialized_ && restingPpgAmp_ > 1.0f)
            ? std::max(0.10f, std::min(2.00f, ampMean / restingPpgAmp_))
            : 1.0f;
    const float vasoDropNorm =
        (ampValid && restingPpgAmpInitialized_ && restingPpgAmp_ > 1.0f)
            ? std::max(0.0f, std::min(1.0f, (0.88f - vasoRatio) / 0.38f))
            : 0.0f;

    // Lớp 1: Hiệu chuẩn nhiệt độ logit (Temperature Scaling) tránh bão hòa 99% sớm
    constexpr float kLogitOffset = 0.50f;
    constexpr float kLogitTemp   = 2.50f;
    const float zCal = std::max(-16.0f, std::min(16.0f, (logit - kLogitOffset) / kLogitTemp));
    const float calProb = 1.0f / (1.0f + std::exp(-zCal));

    // Lớp 2: Cổng sinh lý đa kênh kết hợp Gyroscope + HRV + Co mạch PPG
    const float edaLevelGain = std::max(0.0f, edaMean - kWesadNeutralEdaUs);
    const bool edaActivated = (edaPhasicMean >= 0.10f) ||
                              (edaScrCount >= 4.0f && edaPhasicMean >= 0.06f) ||
                              (edaLevelGain >= 0.50f && edaSlope >= 0.005f) ||
                              (edaLevelGain >= 0.75f);
    const bool edaStrong    = (edaPhasicMean >= 0.22f) ||
                              (edaScrCount >= 6.0f && edaPhasicMean >= 0.14f) ||
                              (edaLevelGain >= 1.35f);

    const bool hrvAutonomic = (hrvDropNorm >= 0.35f);
    const bool isQuietHand = (accNormStd < 0.25f) && (gyroRms < 18.0f);
    const bool isHighPhysicalActivity =
        (gyroRms >= 45.0f) || (accNormStd >= 1.20f && gyroRms >= 22.0f);

    const bool hrElevatedBase =
        (hrMean >= restingHrBpm_ + 10.0f) ||
        (hrMax >= restingHrBpm_ + 15.0f && hrSlope > 0.05f) ||
        (hrMean >= restingHrBpm_ + 7.5f && hrvAutonomic);
    // Nếu đang vung tay/đi lại nhiều mà EDA & HRV không rối loạn -> tránh báo giả stress do vận động
    const bool hrElevated = (isHighPhysicalActivity && !edaStrong && !hrvAutonomic && impacts30s_ == 0)
                                ? (hrMean >= restingHrBpm_ + 16.0f)
                                : hrElevatedBase;
    const bool hrStrong = (hrMean >= restingHrBpm_ + 18.0f) ||
                          (hrMax >= restingHrBpm_ + 22.0f && hrSlope > 0.08f) ||
                          (hrMean >= restingHrBpm_ + 13.0f && hrvDropNorm >= 0.55f);

    const bool repeatedImpact = (impacts30s_ >= 3);
    const bool impactConfirmed =
        repeatedImpact && (rawProb >= 0.40f || edaActivated || hrElevated || hrvAutonomic || impacts30s_ >= 4);
    const bool strictStressConfirmed =
        impactConfirmed || (edaActivated && (hrElevated || hrvAutonomic)) || edaStrong || hrStrong;

    // Lớp 3: Phân bổ xác suất liên tục (loại bỏ vách cứng 45% / 65% để phản ánh biến thiên mượt mà)
    const float hrDeltaMean = std::max(0.0f, hrMean - restingHrBpm_);
    const float hrDeltaPeak = std::max(0.0f, hrMax - restingHrBpm_);
    const float effectiveHrDelta = std::max(hrDeltaMean, 0.70f * hrDeltaPeak);
    const float rawHrNorm = std::min(1.0f, effectiveHrDelta / 25.0f);
    const float hrNorm = (isHighPhysicalActivity && !edaStrong && !hrvAutonomic && impacts30s_ == 0)
                             ? (0.65f * rawHrNorm)
                             : rawHrNorm;

    const float edaRatioGain = std::max(0.0f, (edaMean - kWesadNeutralEdaUs) / 2.5f);
    const float edaPhasicNorm = std::min(1.0f, edaPhasicMean / 0.30f);
    const float scrNorm = std::min(1.0f, edaScrCount / 10.0f);
    const float edaSeverity = std::min(
        1.0f, 0.50f * edaPhasicNorm + 0.30f * std::min(1.0f, edaRatioGain / 0.70f) + 0.20f * scrNorm);
    const float autonomicBoost = 0.70f * hrvDropNorm + 0.30f * vasoDropNorm;
    const float impactNorm = repeatedImpact ? std::min(1.0f, static_cast<float>(impacts30s_) / 5.0f) : 0.0f;
    const float physIntensity = std::min(
        1.0f, 0.48f * hrNorm + 0.52f * edaSeverity + 0.18f * autonomicBoost + 0.15f * impactNorm);

    bool quietGuarded = false;
    bool impactTriggered = false;
    float prob = calProb;
    if (impactConfirmed) {
      const float impactFloor = (impacts30s_ >= 4) ? 0.78f : 0.72f;
      const float strictFloor = std::max(impactFloor, 0.70f + 0.15f * physIntensity);
      const float severityCeiling = 0.73f + 0.26f * physIntensity;
      const float calMix = 0.45f * std::max(0.0f, calProb - 0.50f) / 0.50f + 0.55f * physIntensity;
      prob = strictFloor + (severityCeiling - strictFloor) * std::min(1.0f, calMix);
      impactTriggered = true;
    } else if (isQuietHand && !edaActivated && !hrElevated && !hrvAutonomic) {
      // Đang ngồi học yên tĩnh: xác suất mượt quanh ~10%..44% theo biến thiên thực tế, không ghim cứng 45%
      if (calProb > 0.50f) {
        quietGuarded = true;
      }
      prob = std::min(0.48f, 0.10f + 0.32f * physIntensity + 0.06f * (calProb - 0.5f));
    } else if (!strictStressConfirmed) {
      // Dao động 1 kênh hoặc hồi phục: biến thiên mượt 12%..68% (thoát ATTENTION <55% dễ dàng, hết kẹt 65%)
      const float driver = std::min(
          1.0f, 0.45f * physIntensity + 0.55f * std::max(hrNorm, edaSeverity) + 0.12f * autonomicBoost);
      const float mix = std::min(1.0f, 0.84f * std::sqrt(driver) + 0.16f * calProb);
      prob = std::min(0.68f, 0.12f + 0.56f * mix);
    } else {
      // Đã qua cổng siết chặt -> phân bổ tự nhiên từ 71%..99% theo cường độ đa kênh
      const float strictFloor = 0.70f + 0.15f * physIntensity;
      const float severityCeiling = 0.73f + 0.26f * physIntensity;
      const float calMix = 0.45f * std::max(0.0f, calProb - 0.50f) / 0.50f + 0.55f * physIntensity;
      prob = strictFloor + (severityCeiling - strictFloor) * std::min(1.0f, calMix);
    }

    prob = std::max(0.01f, std::min(0.99f, prob));

    if (!inAttentionState_) {
      if (prob >= kAttentionEnterThreshold) {
        inAttentionState_ = true;
      }
    } else {
      if (prob < kAttentionExitThreshold) {
        inAttentionState_ = false;
      }
    }

    result_.logit = logit;
    result_.rawProbability = std::max(0.01f, std::min(0.99f, rawProb));
    result_.probability = prob;
    result_.hasProbability = true;
    hasCompletedCalibration_ = true;
    result_.edaBaselineUs = edaBaselineUs_;
    result_.restingHrBpm = restingHrBpm_;
    result_.rmssdMs = rmssdMs;
    result_.restingRmssdMs = restingRmssdMs_;
    result_.gyroRms = gyroRms;
    result_.vasoRatio = vasoRatio;
    result_.quietHandGuarded = quietGuarded;
    result_.repeatedImpactTriggered = impactTriggered;
    result_.state = inAttentionState_ ? "ATTENTION" : "NORMAL";
  }

  float extractGyroRms() const {
    const size_t n = accCount_;
    if (n == 0) return 0.0f;
    const size_t start = (accHead_ + kMaxAccSamples - n) % kMaxAccSamples;
    double sqSum = 0.0;
    size_t validCount = 0;
    for (size_t i = 0; i < n; ++i) {
      const size_t idx = (start + i) % kMaxAccSamples;
      if (gyroValidBuf_[idx]) {
        const double g = static_cast<double>(gyroNorm_[idx]);
        sqSum += g * g;
        ++validCount;
      }
    }
    if (validCount < 10) return 0.0f;
    return static_cast<float>(std::sqrt(sqSum / static_cast<double>(validCount)));
  }

  bool extractHrvRmssd(float& outRmssdMs) const {
    const size_t n = hrCount_;
    if (n < 6) {
      outRmssdMs = -1.0f;
      return false;
    }
    const size_t start = (hrHead_ + kMaxHrSamples - n) % kMaxHrSamples;
    float prevRr = NAN;
    double sqDiffSum = 0.0;
    size_t pairCount = 0;
    for (size_t i = 0; i < n; ++i) {
      const float rr = rrBuf_[(start + i) % kMaxHrSamples];
      if (std::isfinite(rr) && rr >= 300.0f && rr <= 1500.0f) {
        if (std::isfinite(prevRr)) {
          const float diff = std::fabs(rr - prevRr);
          if (diff <= 250.0f) {
            sqDiffSum += static_cast<double>(diff) * static_cast<double>(diff);
            ++pairCount;
          }
        }
        prevRr = rr;
      } else {
        prevRr = NAN;
      }
    }
    if (pairCount < 5) {
      outRmssdMs = -1.0f;
      return false;
    }
    outRmssdMs = static_cast<float>(std::sqrt(sqDiffSum / static_cast<double>(pairCount)));
    return true;
  }

  bool extractPpgAmplitude(float& outAmpMean) const {
    const size_t n = hrCount_;
    if (n < 5) {
      outAmpMean = -1.0f;
      return false;
    }
    const size_t start = (hrHead_ + kMaxHrSamples - n) % kMaxHrSamples;
    double sum = 0.0;
    size_t count = 0;
    for (size_t i = 0; i < n; ++i) {
      const float amp = ampBuf_[(start + i) % kMaxHrSamples];
      if (std::isfinite(amp) && amp > 1.0f) {
        sum += static_cast<double>(amp);
        ++count;
      }
    }
    if (count < 5) {
      outAmpMean = -1.0f;
      return false;
    }
    outAmpMean = static_cast<float>(sum / static_cast<double>(count));
    return true;
  }

  void extractEdaFeatures(float* out) const {
    const size_t n = edaCount_;
    const size_t start = (edaHead_ + kMaxEdaSamples - n) % kMaxEdaSamples;
    constexpr float fs = 4.0f;

    float sum = 0.0f, minVal = 1e9f, maxVal = -1e9f;
    for (size_t i = 0; i < n; ++i) {
      const float v = edaBuf_[(start + i) % kMaxEdaSamples];
      sum += v;
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    }
    const float meanVal = sum / static_cast<float>(n);

    float varSum = 0.0f, numSlope = 0.0f, denSlope = 0.0f;
    const float tMean = 0.5f * static_cast<float>(n - 1) / fs;
    for (size_t i = 0; i < n; ++i) {
      const float v = edaBuf_[(start + i) % kMaxEdaSamples];
      const float d = v - meanVal;
      varSum += d * d;
      const float tc = (static_cast<float>(i) / fs) - tMean;
      numSlope += tc * v;
      denSlope += tc * tc;
    }
    const float stdVal = std::sqrt(varSum / static_cast<float>(n));
    const float ptpVal = maxVal - minVal;
    const float slopeVal = (denSlope > 1e-9f) ? (numSlope / denSlope) : 0.0f;

    // Phân rã Tonic / Phasic bằng cửa sổ trượt 5 giây (20 mẫu @ 4 Hz)
    constexpr int kTonicWin = 20;
    constexpr int kHalfWin = kTonicWin / 2;
    float tonicSum = 0.0f, phasicSum = 0.0f, phasicMax = 0.0f;
    std::array<float, kMaxEdaSamples> tonicArr{};
    std::array<float, kMaxEdaSamples> phasicArr{};

    for (size_t i = 0; i < n; ++i) {
      float wSum = 0.0f;
      for (int k = -kHalfWin; k < kHalfWin; ++k) {
        int idx = static_cast<int>(i) + k;
        if (idx < 0) idx = 0;
        if (idx >= static_cast<int>(n)) idx = static_cast<int>(n) - 1;
        wSum += edaBuf_[(start + static_cast<size_t>(idx)) % kMaxEdaSamples];
      }
      const float tVal = wSum / static_cast<float>(kTonicWin);
      const float rawVal = edaBuf_[(start + i) % kMaxEdaSamples];
      const float pVal = std::max(0.0f, rawVal - tVal);
      tonicArr[i] = tVal;
      phasicArr[i] = pVal;
      tonicSum += tVal;
      phasicSum += pVal;
      if (pVal > phasicMax) phasicMax = pVal;
    }

    const float tonicMean = tonicSum / static_cast<float>(n);
    const float phasicMean = phasicSum / static_cast<float>(n);
    float tonicVar = 0.0f, phasicVar = 0.0f;
    for (size_t i = 0; i < n; ++i) {
      const float dt = tonicArr[i] - tonicMean;
      const float dp = phasicArr[i] - phasicMean;
      tonicVar += dt * dt;
      phasicVar += dp * dp;
    }
    const float tonicStd = std::sqrt(tonicVar / static_cast<float>(n));
    const float phasicStd = std::sqrt(phasicVar / static_cast<float>(n));

    const float durationScale = 60.0f / (static_cast<float>(n) / fs);
    const float phasicAuc = (phasicSum / fs) * durationScale;

    size_t scrPeaks = 0;
    float scrAmpSum = 0.0f;
    int lastPeakIdx = -4;
    for (size_t i = 1; i + 1 < n; ++i) {
      const float p = phasicArr[i];
      if (p >= 0.01f && p > phasicArr[i - 1] && p >= phasicArr[i + 1]) {
        if (static_cast<int>(i) - lastPeakIdx >= 4) {
          ++scrPeaks;
          scrAmpSum += p;
          lastPeakIdx = static_cast<int>(i);
        }
      }
    }
    const float scrCount = static_cast<float>(scrPeaks) * durationScale;
    const float scrAmpMean = (scrPeaks > 0) ? (scrAmpSum / static_cast<float>(scrPeaks)) : 0.0f;

    out[0]  = meanVal;
    out[1]  = stdVal;
    out[2]  = minVal;
    out[3]  = maxVal;
    out[4]  = ptpVal;
    out[5]  = slopeVal;
    out[6]  = tonicMean;
    out[7]  = tonicStd;
    out[8]  = phasicMean;
    out[9]  = phasicMax;
    out[10] = phasicStd;
    out[11] = phasicAuc;
    out[12] = scrCount;
    out[13] = scrAmpMean;
  }

  void extractAccFeatures(float* out) const {
    const size_t n = accCount_;
    const size_t start = (accHead_ + kMaxAccSamples - n) % kMaxAccSamples;

    float sumNorm = 0.0f, sumX = 0.0f, sumY = 0.0f, sumZ = 0.0f;
    for (size_t i = 0; i < n; ++i) {
      const size_t idx = (start + i) % kMaxAccSamples;
      sumNorm += accNorm_[idx];
      sumX += accX_[idx];
      sumY += accY_[idx];
      sumZ += accZ_[idx];
    }
    const float rawMeanNorm = sumNorm / static_cast<float>(n);
    const float meanX = sumX / static_cast<float>(n);
    const float meanY = sumY / static_cast<float>(n);
    const float meanZ = sumZ / static_cast<float>(n);

    constexpr float kWesadGravityRef = 9.7492342f;
    float varNorm = 0.0f, varX = 0.0f, varY = 0.0f, varZ = 0.0f;
    float minNorm = 1e9f, maxNorm = -1e9f, energySum = 0.0f;
    size_t motionCount = 0;

    for (size_t i = 0; i < n; ++i) {
      const size_t idx = (start + i) % kMaxAccSamples;
      const float deltaNorm = accNorm_[idx] - rawMeanNorm;
      const float adjNorm = kWesadGravityRef + deltaNorm;
      varNorm += deltaNorm * deltaNorm;
      if (adjNorm < minNorm) minNorm = adjNorm;
      if (adjNorm > maxNorm) maxNorm = adjNorm;
      energySum += adjNorm * adjNorm;
      if (std::fabs(deltaNorm) > 0.50f) ++motionCount;

      const float dx = accX_[idx] - meanX;
      const float dy = accY_[idx] - meanY;
      const float dz = accZ_[idx] - meanZ;
      varX += dx * dx;
      varY += dy * dy;
      varZ += dz * dz;
    }

    const float invN = 1.0f / static_cast<float>(n);
    out[14] = kWesadGravityRef;
    out[15] = std::sqrt(varNorm * invN);
    out[16] = minNorm;
    out[17] = maxNorm;
    out[18] = maxNorm - minNorm;
    out[19] = energySum * invN;
    out[20] = static_cast<float>(motionCount) * invN;
    out[21] = 2.5510299f;
    out[22] = std::sqrt(varX * invN);
    out[23] = -0.7888136f;
    out[24] = std::sqrt(varY * invN);
    out[25] = 1.5876733f;
    out[26] = std::sqrt(varZ * invN);
  }

  void extractHrFeatures(float* out) const {
    const size_t n = hrCount_;
    const size_t start = (hrHead_ + kMaxHrSamples - n) % kMaxHrSamples;

    std::array<float, kMaxHrSamples> imputed{};
    std::array<float, kMaxHrSamples> weights{};
    std::array<bool, kMaxHrSamples> validMask{};
    size_t validCount = 0;
    float validSum = 0.0f;
    int firstValidIdx = -1;

    for (size_t i = 0; i < n; ++i) {
      const float v = hrBuf_[(start + i) % kMaxHrSamples];
      const bool ok = std::isfinite(v) && v >= 40.0f && v <= 200.0f;
      validMask[i] = ok;
      imputed[i] = v;
      weights[i] = ok ? kGreenHrWeight : 0.0f;
      if (ok) {
        ++validCount;
        validSum += v;
        if (firstValidIdx < 0) firstValidIdx = static_cast<int>(i);
      }
    }

    const float validRatio = static_cast<float>(validCount) / static_cast<float>(n);
    const float isValid = (validRatio >= 0.30f) ? 1.0f : 0.0f;
    const float scaledValidCount = validRatio * 60.0f;

    if (validCount == 0) {
      out[27] = 0.0f;
      out[28] = 0.0f;
      out[29] = 0.0f;
      out[30] = restingHrBpm_;
      out[31] = 0.0f;
      out[32] = restingHrBpm_;
      out[33] = restingHrBpm_;
      out[34] = 0.0f;
      out[35] = 0.0f;
      return;
    }

    // Mẫu chuẩn nét xanh có trọng số 1.0; mẫu duy trì nét vàng (tối đa 15s) có trọng số 0.25
    float lastVal = NAN;
    int staleCount = 0;
    for (size_t i = 0; i < n; ++i) {
      if (validMask[i]) {
        lastVal = imputed[i];
        staleCount = 0;
      } else if (std::isfinite(lastVal) && staleCount < 15) {
        imputed[i] = lastVal;
        weights[i] = kYellowHrWeight;
        ++staleCount;
      } else {
        imputed[i] = NAN;
        weights[i] = kYellowHrWeight;
      }
    }
    for (int i = 0; i < firstValidIdx; ++i) {
      imputed[static_cast<size_t>(i)] = imputed[static_cast<size_t>(firstValidIdx)];
      weights[static_cast<size_t>(i)] = kYellowHrWeight;
    }

    const float meanValid = validSum / static_cast<float>(validCount);
    float wSum = 0.0f, wValSum = 0.0f;
    float minVal = 1e9f, maxVal = -1e9f;
    for (size_t i = 0; i < n; ++i) {
      if (!std::isfinite(imputed[i])) imputed[i] = meanValid;
      const float v = imputed[i];
      const float w = weights[i];
      wSum += w;
      wValSum += w * v;
      // Chỉ lấy cực tiểu/cực đại từ các mẫu chuẩn nét xanh (không để nét vàng tạo đỉnh/đáy giả)
      if (validMask[i]) {
        if (v < minVal) minVal = v;
        if (v > maxVal) maxVal = v;
      }
    }
    const float hrMean = (wSum > 1e-6f) ? (wValSum / wSum) : meanValid;

    float wVarSum = 0.0f, tWMean = 0.0f;
    for (size_t i = 0; i < n; ++i) {
      tWMean += weights[i] * static_cast<float>(i);
    }
    tWMean = (wSum > 1e-6f) ? (tWMean / wSum) : 0.0f;

    float numSlope = 0.0f, denSlope = 0.0f;
    for (size_t i = 0; i < n; ++i) {
      const float v = imputed[i];
      const float w = weights[i];
      const float d = v - hrMean;
      wVarSum += w * d * d;
      const float tc = static_cast<float>(i) - tWMean;
      numSlope += w * tc * d;
      denSlope += w * tc * tc;
    }
    const float hrStd = (validCount >= 2 && wSum > 1e-6f) ? std::sqrt(wVarSum / wSum) : 0.0f;
    const float hrSlope = (denSlope > 1e-6f) ? (numSlope / denSlope) : 0.0f;

    out[27] = scaledValidCount;
    out[28] = validRatio;
    out[29] = isValid;
    out[30] = hrMean;
    out[31] = hrStd;
    out[32] = minVal;
    out[33] = maxVal;
    out[34] = maxVal - minVal;
    out[35] = hrSlope;
  }

  Result result_{};
  std::array<float, kMaxEdaSamples> edaBuf_{};
  std::array<float, kMaxAccSamples> accX_{}, accY_{}, accZ_{}, accNorm_{}, gyroNorm_{};
  std::array<bool, kMaxAccSamples> gyroValidBuf_{};
  std::array<float, kMaxHrSamples> hrBuf_{}, rrBuf_{}, ampBuf_{};

  size_t edaHead_ = 0, edaCount_ = 0;
  size_t accHead_ = 0, accCount_ = 0;
  size_t hrHead_  = 0, hrCount_  = 0;
  size_t hrSamplesSinceLastStep_ = 0;

  uint64_t lastEdaSampleMs_ = 0;
  uint64_t lastAccSampleMs_ = 0;
  uint64_t lastHrSampleMs_  = 0;
  uint64_t noContactSinceMs_ = 0;
  uint64_t recalibGraceSinceMs_ = 0;

  float adcFast_ = 0.0f;
  float adcSlow_ = 0.0f;
  float lastAcceptedAdc_ = 0.0f;
  float lastEdaUs_ = kWesadNeutralEdaUs;
  bool edaBaselineInitialized_ = false;
  float edaBaselineSum_ = 0.0f;
  size_t edaBaselineSamples_ = 0;
  float edaBaselineUs_ = kWesadNeutralEdaUs;

  bool adcBaselineInitialized_ = false;
  float adcBaselineSum_ = 0.0f;
  size_t adcBaselineSamples_ = 0;
  float adcBaselineRaw_ = 1800.0f;

  size_t restingHrCount_ = 0;
  float restingHrSum_ = 0.0f;
  float restingHrBpm_ = 75.0f;
  float latestHrForBaseline_ = 75.0f;
  bool hasLatestHrForBaseline_ = false;

  bool restingRmssdInitialized_ = false;
  float restingRmssdSum_ = 0.0f;
  size_t restingRmssdCount_ = 0;
  float restingRmssdMs_ = -1.0f;

  bool restingPpgAmpInitialized_ = false;
  float restingPpgAmpSum_ = 0.0f;
  size_t restingPpgAmpCount_ = 0;
  float restingPpgAmp_ = 0.0f;

  uint8_t impacts30s_ = 0;
  bool adcInitialized_ = false;
  bool hasStartedWithHr_ = false;
  bool hasCompletedCalibration_ = false;
  bool inAttentionState_ = false;
  bool waitForFreshHrAfterDrop_ = false;
};

}  // namespace asd

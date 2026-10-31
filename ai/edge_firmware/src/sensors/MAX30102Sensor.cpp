#include "MAX30102Sensor.h"

#include <Wire.h>
#undef I2C_BUFFER_LENGTH
#include <MAX30105.h>
#include <algorithm>   // std::sort

// =============================================================================
Availability MAX30102Sensor::begin() {
  if (sensor_ == nullptr) {
    sensor_ = new MAX30105();
    if (sensor_ == nullptr) {
      Serial.println(F("[MAX30102] LỖI: Cấp phát bộ nhớ thất bại"));
      status_ = PPGStatus::ERROR;
      return Availability::ERROR;
    }
  }

  lastRetryMs_ = millis();

  if (!sensor_->begin(Wire, I2C_CLOCK_HZ, I2C_ADDR_MAX30102)) {
    ready_  = false;
    status_ = PPGStatus::DISCONNECTED;
    return Availability::UNAVAILABLE;
  }

  sensor_->setup(
      PPG_LED_BRIGHTNESS, PPG_SAMPLE_AVERAGE, PPG_LED_MODE,
      PPG_SAMPLE_RATE_HZ, PPG_PULSE_WIDTH,    PPG_ADC_RANGE
  );
  sensor_->clearFIFO();

  resetCalculations();
  ready_  = true;
  status_ = PPGStatus::NO_FINGER;
  Serial.println(F("[MAX30102] OK — Khởi tạo thành công chế độ SpO2 (Non-blocking FIFO)"));
  return Availability::READY;
}

void MAX30102Sensor::resetCalculations() {
  irDc_              = 0.0f;
  redDc_             = 0.0f;
  biquadX1_          = 0.0f;
  biquadX2_          = 0.0f;
  biquadY1_          = 0.0f;
  biquadY2_          = 0.0f;
  acFiltered_        = 0.0f;
  prevAc_            = 0.0f;
  prev2Ac_           = 0.0f;
  acMax_             = 0.0f;
  acMin_             = 0.0f;
  redBiquadX1_       = 0.0f;
  redBiquadX2_       = 0.0f;
  redBiquadY1_       = 0.0f;
  redBiquadY2_       = 0.0f;
  redAcMax_          = 0.0f;
  redAcMin_          = 0.0f;
  lastBeatMs_        = 0;
  lastRrIntervalMs_  = 0;
  rateSpot_          = 0;
  beatAvg_           = 0.0f;
  medianBpm_         = 0.0f;
  validBeatCount_    = 0;
  for (size_t i = 0; i < kRateBufferSize; ++i) rates_[i] = 0.0f;

  bufferIdx_   = 0;
  bufferCount_ = 0;
  spo2Avg_     = 0.0f;
  rawSpo2_     = 0.0f;

  hrFilter_.reset();
  spo2Filter_.reset();
}

// =============================================================================
// Tính TRUNG VỊ (Median) từ mảng rates_[] chỉ lấy các slot hợp lệ (> 0)
// Kích thước kRateBufferSize = 8: sử dụng insertion sort ổn định
// =============================================================================
float MAX30102Sensor::computeMedianBpm() {
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

// =============================================================================
// Thuật toán tách sóng PPG y sinh & Phát hiện nhịp tim chống đếm nhịp đôi:
// 1. Tách thành phần DC trượt (High-pass stage)
// 2. Bộ lọc thông thấp Butterworth bậc 2 (fc = 2.5 Hz @ fs = 50 Hz):
//    Triệt tiêu dicrotic notch (>3.5 Hz) và triệt tiêu rung giật vi cơ
// 3. Cửa sổ thời gian trơ sinh lý động (Adaptive Physiological Blanking Window):
//    Tuyệt đối không đếm sóng phản xạ tâm trương / dicrotic wave ở khoảng 300-350ms
// =============================================================================
bool MAX30102Sensor::detectBeat(uint32_t irValue, uint32_t redValue, unsigned long now) {
  const float x  = static_cast<float>(irValue);
  const float rx = static_cast<float>(redValue);

  // 1. Tách thành phần DC cho cả 2 kênh IR và Red
  if (irDc_ == 0.0f) {
    irDc_  = x;
    redDc_ = rx;
  } else {
    irDc_  = irDc_ * 0.98f + x * 0.02f;
    redDc_ = redDc_ * 0.98f + rx * 0.02f;
  }

  const float ac    = x - irDc_;
  const float redAc = rx - redDc_;

  // 2. Bộ lọc thông thấp Butterworth bậc 2 (fc = 2.5 Hz @ fs = 50 Hz)
  // Hệ số chuẩn hóa:
  static constexpr float kB0 =  0.020083f;
  static constexpr float kB1 =  0.040167f;
  static constexpr float kB2 =  0.020083f;
  static constexpr float kA1 = -1.561018f;
  static constexpr float kA2 =  0.641351f;

  const float acF = kB0 * ac + kB1 * biquadX1_ + kB2 * biquadX2_
                  - kA1 * biquadY1_ - kA2 * biquadY2_;
  biquadX2_   = biquadX1_;
  biquadX1_   = ac;
  biquadY2_   = biquadY1_;
  biquadY1_   = acF;
  acFiltered_ = acF;

  const float redAcF = kB0 * redAc + kB1 * redBiquadX1_ + kB2 * redBiquadX2_
                     - kA1 * redBiquadY1_ - kA2 * redBiquadY2_;
  redBiquadX2_ = redBiquadX1_;
  redBiquadX1_ = redAc;
  redBiquadY2_ = redBiquadY1_;
  redBiquadY1_ = redAcF;

  // 3. Theo dõi biên độ đỉnh-đáy thích ứng cho cả 2 kênh
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

  if (redAcF > redAcMax_) {
    redAcMax_ = redAcF;
  } else {
    redAcMax_ -= (redAcMax_ - 0.0f) * 0.006f;
  }

  if (redAcF < redAcMin_) {
    redAcMin_ = redAcF;
  } else {
    redAcMin_ += (0.0f - redAcMin_) * 0.006f;
  }

  const float vpp    = acMax_ - acMin_;
  const float redVpp = redAcMax_ - redAcMin_;

  // 4. Bắt đỉnh sóng mạch tâm thu (Systolic Peak Detection)
  const bool isPeak = (prevAc_ > prev2Ac_) && (prevAc_ >= acFiltered_);
  // Ngưỡng thích ứng: Đỉnh sóng phải vượt qua 60% biên độ peak-to-peak
  const float threshold = acMin_ + vpp * 0.60f;

  bool beatDetected = false;

  if (isPeak && (prevAc_ > threshold) && (vpp >= PPG_AC_MIN_AMPLITUDE)) {
    if (lastBeatMs_ > 0) {
      const unsigned long delta = now - lastBeatMs_;

      // ── Thời gian trơ sinh lý động (Adaptive Physiological Blanking Window) ──
      // Người nghỉ ngơi (BPM ~ 70 => RR ~ 857ms) có thời gian trơ ít nhất 514ms.
      // Dicrotic notch (ở 300-350ms) sẽ bị loại bỏ hoàn toàn, không thể gây đếm nhịp đôi.
      unsigned long blankingWindow = 400; // Mặc định 1-2 nhịp đầu (tương đương max 150 BPM)
      if (lastRrIntervalMs_ > 0) {
        blankingWindow = static_cast<unsigned long>(lastRrIntervalMs_ * 0.60f);
        if (blankingWindow < 360) blankingWindow = 360; // Giới hạn dưới: 360ms (max 166 BPM)
        if (blankingWindow > 650) blankingWindow = 650; // Giới hạn trên để không bỏ lỡ khi nhịp tăng
      }

      if (delta >= blankingWindow && delta <= 1800) {
        // Kiểm tra loại trừ sóng phản xạ harmonic (xấp xỉ 1/2 khoảng RR trước đó)
        bool isHarmonic = false;
        if (lastRrIntervalMs_ > 0 && validBeatCount_ >= 2) {
          long halfRr = static_cast<long>(lastRrIntervalMs_ / 2);
          if (labs(static_cast<long>(delta) - halfRr) < 70) {
            isHarmonic = true;
          }
        }

        if (!isHarmonic) {
          float instantBpm = 60000.0f / static_cast<float>(delta);
          if (instantBpm >= HR_MIN_PHYSIOLOGICAL && instantBpm <= HR_MAX_PHYSIOLOGICAL) {
            rates_[rateSpot_++] = instantBpm;
            rateSpot_ %= kRateBufferSize;

            lastRrIntervalMs_ = delta;
            lastBeatMs_       = now;
            validBeatCount_++;
            beatDetected      = true;

            // ── Bước 1: Tính trung bình trượt thô
            float sum = 0.0f;
            size_t count = 0;
            for (size_t i = 0; i < kRateBufferSize; ++i) {
              if (rates_[i] > 0.0f) {
                sum += rates_[i];
                ++count;
              }
            }
            if (count > 0) {
              beatAvg_ = sum / static_cast<float>(count);
            }

            // ── Bước 2: Tính TRUNG VỊ khoảng RR (loại bỏ nhịp bất thường)
            medianBpm_ = computeMedianBpm();

            // ── Bước 3: EMA nhẹ trên TRUNG VỊ (làm mượt hiển thị)
            hrFilter_.update(medianBpm_);

            // ── Bước 4: Tính toán SpO2 đồng bộ ngay tại đỉnh xung mạch
            if (irDc_ > 10000.0f && redDc_ > 10000.0f && vpp >= PPG_AC_MIN_AMPLITUDE && redVpp >= PPG_AC_MIN_AMPLITUDE) {
              float r = (redVpp / redDc_) / (vpp / irDc_);
              if (r >= 0.30f && r <= 1.80f) {
                // Đa thức hiệu chuẩn Maxim Integrated RD117
                float instantSpO2 = -45.060f * r * r + 30.354f * r + 94.845f;
                if (instantSpO2 > SPO2_MAX_PHYSIOLOGICAL) instantSpO2 = SPO2_MAX_PHYSIOLOGICAL;
                if (instantSpO2 < SPO2_MIN_PHYSIOLOGICAL) instantSpO2 = SPO2_MIN_PHYSIOLOGICAL;

                rawSpo2_ = instantSpO2;
                spo2Avg_ = spo2Filter_.update(instantSpO2);
              }
            }
          }
        }
      } else if (delta > 1800) {
        lastBeatMs_ = now;
        lastRrIntervalMs_ = 0;
      }
    } else {
      lastBeatMs_ = now;
    }
  }

  // Cập nhật lịch sử đỉnh
  prev2Ac_ = prevAc_;
  prevAc_  = acFiltered_;

  // Quá 3500ms không có nhịp mới thì reset nhịp trung bình và bộ lọc
  if (lastBeatMs_ > 0 && (now - lastBeatMs_ > 3500)) {
    beatAvg_           = 0.0f;
    medianBpm_         = 0.0f;
    lastRrIntervalMs_  = 0;
    validBeatCount_    = 0;
    hrFilter_.reset();
  }

  return beatDetected;
}

MAX30102Data MAX30102Sensor::read() {
  MAX30102Data data{};

  // Tự động kết nối lại định kỳ không nghẽn bus nếu cảm biến bị ngắt
  if (!ready_ || sensor_ == nullptr) {
    const unsigned long now = millis();
    if (now - lastRetryMs_ >= I2C_RETRY_INTERVAL_MS) {
      lastRetryMs_ = now;
      if (begin() == Availability::READY) {
        Serial.println(F("[MAX30102] >>> Phục hồi kết nối thành công! <<<"));
      }
    }
    data.status = PPGStatus::DISCONNECTED;
    return data;
  }

  // 1. Đọc FIFO theo polling; cần đo thời gian I2C thực tế
  sensor_->check();

  uint32_t irSamples[kFifoBufferSize];
  uint32_t redSamples[kFifoBufferSize];
  size_t sampleCount = 0;
  bool hasNewData = false;

  while (sensor_->available()) {
    latestIr_  = sensor_->getFIFOIR();
    latestRed_ = sensor_->getFIFORed();
    sensor_->nextSample();
    if (sampleCount < kFifoBufferSize) {
      irSamples[sampleCount]  = latestIr_;
      redSamples[sampleCount] = latestRed_;
      sampleCount++;
    }
    hasNewData = true;
  }

  data.irValue        = latestIr_;
  data.redValue       = latestRed_;
  data.fingerDetected = (data.irValue >= PPG_IR_FINGER_THRESHOLD);

  // 2. Kiểm tra trạng thái ngón tay
  if (!data.fingerDetected) {
    resetCalculations();
    status_         = PPGStatus::NO_FINGER;
    data.status     = status_;
    data.heartRate  = 0.0f;
    data.spO2       = 0.0f;
    data.valid      = false;
    return data;
  }

  const unsigned long now = millis();

  // 3. Xử lý từng mẫu FIFO đồng bộ thời gian lấy mẫu (50 Hz = 20ms)
  if (hasNewData) {
    const unsigned long samplePeriodMs = PPG_SAMPLE_PERIOD_MS;
    for (size_t i = 0; i < sampleCount; ++i) {
      const size_t samplesAfter = sampleCount - i - 1;
      const unsigned long sampleTime =
          now - samplesAfter * samplePeriodMs;
      detectBeat(irSamples[i], redSamples[i], sampleTime);
    }
  }

  data.pulseAmplitude  = acMax_ - acMin_;
  data.rawHeartRate    = beatAvg_;
  data.medianHeartRate = medianBpm_;
  data.heartRate       = hrFilter_.isInitialized() ? hrFilter_.getValue() : medianBpm_;
  data.rawSpO2         = rawSpo2_;
  data.spO2            = spo2Filter_.isInitialized() ? spo2Filter_.getValue() : spo2Avg_;

  // 4. Xác định trạng thái ổn định tín hiệu
  if (validBeatCount_ < 2 || data.heartRate < HR_MIN_PHYSIOLOGICAL) {
    status_    = PPGStatus::PULSE_ACQUIRING;
    data.valid = false;
  } else {
    status_    = PPGStatus::VALID;
    data.valid = true;
  }

  data.status = status_;
  return data;
}


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
  irDc_           = 0.0f;
  acSmoothed_     = 0.0f;
  prevAc_         = 0.0f;
  prev2Ac_        = 0.0f;
  acMax_          = 0.0f;
  acMin_          = 0.0f;
  lastBeatMs_     = 0;
  rateSpot_       = 0;
  beatAvg_        = 0.0f;
  medianBpm_      = 0.0f;
  validBeatCount_ = 0;
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
// Buffer kích thước nhỏ (kRateBufferSize = 4): dùng insertion sort đơn giản.
// =============================================================================
float MAX30102Sensor::computeMedianBpm() {
  // Thu thập các giá trị hợp lệ (> 0) từ circular buffer
  float tmp[kRateBufferSize];
  size_t n = 0;
  for (size_t i = 0; i < kRateBufferSize; ++i) {
    if (rates_[i] > 0.0f) tmp[n++] = rates_[i];
  }
  if (n == 0) return 0.0f;
  if (n == 1) return tmp[0];

  // Insertion sort (n nhỏ ≤ 4, không cần std::sort)
  for (size_t i = 1; i < n; ++i) {
    float key = tmp[i];
    int j = static_cast<int>(i) - 1;
    while (j >= 0 && tmp[j] > key) {
      tmp[j + 1] = tmp[j];
      --j;
    }
    tmp[j + 1] = key;
  }

  // Lấy phần tử giữa (hoặc trung bình 2 phần tử giữa khi n chẵn)
  if (n % 2 == 1) {
    return tmp[n / 2];
  } else {
    return (tmp[n / 2 - 1] + tmp[n / 2]) * 0.5f;
  }
}

bool MAX30102Sensor::detectBeat(uint32_t irValue, unsigned long now) {
  const float x = static_cast<float>(irValue);

  // 1. Tách thành phần DC bằng bộ lọc IIR thông thấp
  if (irDc_ == 0.0f) {
    irDc_ = x;
  } else {
    irDc_ = irDc_ * 0.95f + x * 0.05f;
  }

  // Tín hiệu AC dao động quanh mức 0
  const float ac = x - irDc_;

  // 2. Làm mượt tín hiệu AC
  if (acSmoothed_ == 0.0f) {
    acSmoothed_ = ac;
  } else {
    acSmoothed_ = acSmoothed_ * 0.65f + ac * 0.35f;
  }

  // 3. Theo dõi biên độ cực đại và cực tiểu AC thích ứng
  if (acSmoothed_ > acMax_) {
    acMax_ = acSmoothed_;
  } else {
    acMax_ -= (acMax_ - 0.0f) * 0.005f;
  }

  if (acSmoothed_ < acMin_) {
    acMin_ = acSmoothed_;
  } else {
    acMin_ += (0.0f - acMin_) * 0.005f;
  }

  const float vpp = acMax_ - acMin_;

  // 4. Bắt đỉnh sóng mạch (Systolic Peak Detection)
  const bool isPeak = (prevAc_ > prev2Ac_) && (prevAc_ >= acSmoothed_);
  const float threshold = acMin_ + vpp * 0.50f;

  bool beatDetected = false;

  // Ngưỡng biên độ sóng tối thiểu (PPG_AC_MIN_AMPLITUDE = 50 counts)
  if (isPeak && (prevAc_ > threshold) && (vpp >= PPG_AC_MIN_AMPLITUDE)) {
    if (lastBeatMs_ > 0) {
      const unsigned long delta = now - lastBeatMs_;
      // Khoảng thời gian hợp lệ giữa 2 nhịp tim: 300ms (200 BPM) đến 1500ms (40 BPM)
      if (delta >= 300 && delta <= 1500) {
        float instantBpm = 60000.0f / static_cast<float>(delta);
        if (instantBpm >= HR_MIN_PHYSIOLOGICAL && instantBpm <= HR_MAX_PHYSIOLOGICAL) {
          rates_[rateSpot_++] = instantBpm;
          rateSpot_ %= kRateBufferSize;

          // ── Bước 1: Tính TRUNG BÌNH TRƯỢT thô (rawHeartRate)
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

          validBeatCount_++;
          beatDetected = true;
        }
      } else if (delta > 1500) {
        lastBeatMs_ = now;
      }
    }
    lastBeatMs_ = now;
  }

  // Cập nhật lịch sử đỉnh
  prev2Ac_ = prevAc_;
  prevAc_  = acSmoothed_;

  // Quá 3500ms không có nhịp mới thì reset nhịp trung bình và bộ lọc
  if (lastBeatMs_ > 0 && (now - lastBeatMs_ > 3500)) {
    beatAvg_        = 0.0f;
    medianBpm_      = 0.0f;
    validBeatCount_ = 0;
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

  // 1. Lấy dữ liệu FIFO KHÔNG NGHẼN BUS (Non-blocking FIFO polling)
  // Chỉ gọi sensor_->check() một lần. Hàm này đọc thanh ghi FIFO pointers và nạp mẫu.
  // Tuyệt đối không gọi getIR() / getRed() lặp lại vì sẽ gây nghẽn bus I2C (safeCheck 250ms).
  sensor_->check();

  uint32_t irSamples[kFifoBufferSize];
  size_t sampleCount = 0;
  bool hasNewData = false;
  while (sensor_->available()) {
    latestIr_  = sensor_->getFIFOIR();
    latestRed_ = sensor_->getFIFORed();
    sensor_->nextSample();
    if (sampleCount < kFifoBufferSize) {
      irSamples[sampleCount++] = latestIr_;
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

  // 3. Xử lý từng mẫu FIFO để không bỏ qua đỉnh khi loop bị trễ.
  if (hasNewData) {
    const unsigned long samplePeriodMs = 1000UL / PPG_SAMPLE_RATE_HZ;
    for (size_t i = 0; i < sampleCount; ++i) {
      const size_t samplesAfter = sampleCount - i - 1;
      const unsigned long sampleTime =
          now - samplesAfter * samplePeriodMs;
      detectBeat(irSamples[i], sampleTime);
    }
  }
  data.pulseAmplitude = acMax_ - acMin_;

  // 4. Tính toán SpO2 (%) bằng tỉ số AC/DC
  if (hasNewData) {
    irBuffer_[bufferIdx_]  = data.irValue;
    redBuffer_[bufferIdx_] = data.redValue;
    bufferIdx_ = (bufferIdx_ + 1) % kSampleBufferSize;
    if (bufferCount_ < kSampleBufferSize) bufferCount_++;

    if (bufferCount_ >= 25) {
      uint32_t irMin = irBuffer_[0], irMax = irBuffer_[0];
      uint32_t redMin = redBuffer_[0], redMax = redBuffer_[0];
      uint64_t irSum = 0, redSum = 0;

      for (size_t i = 0; i < bufferCount_; ++i) {
        if (irBuffer_[i] < irMin) irMin = irBuffer_[i];
        if (irBuffer_[i] > irMax) irMax = irBuffer_[i];
        irSum += irBuffer_[i];

        if (redBuffer_[i] < redMin) redMin = redBuffer_[i];
        if (redBuffer_[i] > redMax) redMax = redBuffer_[i];
        redSum += redBuffer_[i];
      }

      float irDc  = static_cast<float>(irSum) / static_cast<float>(bufferCount_);
      float redDc = static_cast<float>(redSum) / static_cast<float>(bufferCount_);
      float irAc  = static_cast<float>(irMax - irMin);
      float redAc = static_cast<float>(redMax - redMin);

      if (irDc > 1000.0f && redDc > 1000.0f && irAc >= PPG_AC_MIN_AMPLITUDE && redAc >= PPG_AC_MIN_AMPLITUDE) {
        float r = (redAc / redDc) / (irAc / irDc);
        // Ước tính SpO2 quang học (Optical estimate)
        if (r >= 0.35f && r <= 1.8f) {
          float instantSpO2 = 110.0f - 25.0f * r;
          if (instantSpO2 > SPO2_MAX_PHYSIOLOGICAL) instantSpO2 = SPO2_MAX_PHYSIOLOGICAL;
          if (instantSpO2 < SPO2_MIN_PHYSIOLOGICAL) instantSpO2 = SPO2_MIN_PHYSIOLOGICAL;

          // Bước 3: EMA nhẹ — làm mượt SpO2 không làm biến dạng đỉnh sóng
          rawSpo2_ = instantSpO2;
          spo2Avg_ = spo2Filter_.update(instantSpO2);
        }
      }
    }
  }

  data.rawHeartRate    = beatAvg_;
  data.medianHeartRate = medianBpm_;
  data.heartRate       = hrFilter_.isInitialized() ? hrFilter_.getValue() : medianBpm_;
  data.rawSpO2         = rawSpo2_;
  data.spO2            = spo2Filter_.isInitialized() ? spo2Filter_.getValue() : spo2Avg_;

  // 5. Xác định trạng thái ổn định tín hiệu
  if (validBeatCount_ < 1 || data.heartRate < HR_MIN_PHYSIOLOGICAL) {
    status_    = PPGStatus::PULSE_ACQUIRING;
    data.valid = false;
  } else {
    status_    = PPGStatus::VALID;
    data.valid = true;
  }

  data.status = status_;
  return data;
}

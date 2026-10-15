#include "GSRSensor.h"

// =============================================================================
Availability GSRSensor::begin() {
  pin_ = PIN_GSR_ADC;
  if (pin_ < 0) {
    Serial.println(F("[GSR] LỖI: Chưa cấu hình chân ADC"));
    status_ = GSRStatus::ERROR;
    return Availability::ERROR;
  }

  analogReadResolution(GSR_ADC_RESOLUTION);
  pinMode(pin_, INPUT);
  (void)analogRead(pin_); // Đọc bỏ mẫu đầu để ổn định ADC

  ready_ = true;
  status_ = GSRStatus::DISCONNECTED;
  resetBaseline();

  Serial.printf("[GSR] OK — ADC chân GPIO%d, độ phân giải %d-bit, full-scale 3.3 V\n",
                pin_, GSR_ADC_RESOLUTION);
  return Availability::READY;
}

void GSRSensor::resetBaseline() {
  isCalibrating_ = false;
  calibrationStartMs_ = 0;
  calibMvSum_ = 0;
  calibSampleCount_ = 0;
  baselineMv_ = 0.0f;
  baselineConductance_ = 0.0f;
  voltageFilter_.reset();
  conductanceFilter_.reset();
}

GSRData GSRSensor::read() {
  GSRData data{};
  if (!ready_ || pin_ < 0) {
    data.status = GSRStatus::ERROR;
    return data;
  }

  // 1. Lấy mẫu ADC trung bình rồi quy đổi tuyến tính theo full-scale 3.3 V.
  uint32_t adcRawAcc = 0;
  for (unsigned i = 0; i < GSR_AVERAGING_SAMPLES; ++i) {
    adcRawAcc += analogRead(pin_);
  }
  data.rawADC = static_cast<uint16_t>(
      (adcRawAcc + GSR_AVERAGING_SAMPLES / 2U) / GSR_AVERAGING_SAMPLES);
  const float rawVoltage = static_cast<float>(data.rawADC) *
                           static_cast<float>(GSR_ADC_FULL_SCALE_MV) /
                           (static_cast<float>(GSR_ADC_MAX_VALUE) * 1000.0f);
  const uint32_t rawVoltage_mV =
      (static_cast<uint32_t>(data.rawADC) * GSR_ADC_FULL_SCALE_MV +
       GSR_ADC_MAX_VALUE / 2U) /
      GSR_ADC_MAX_VALUE;

  data.rawVoltage    = rawVoltage;
  data.rawVoltage_mV = rawVoltage_mV;

  // 2. Phân loại trạng thái phần cứng dựa trên đặc tính Op-amp LM324
  // LM324 nguồn đơn (single-supply 3.3V) có điện áp bão hòa thấp Vol ≈ 0.05V - 0.15V.
  // Khi hở mạch (chưa đeo điện cực), ngõ ra op-amp sụt về rail thấp (< 150 mV).
  if (rawVoltage_mV < GSR_HARDWARE_OPEN_MV) {
    status_ = GSRStatus::DISCONNECTED;
    resetBaseline();
    data.voltage           = rawVoltage;
    data.voltage_mV        = rawVoltage_mV;
    data.status            = status_;
    data.resistance        = 0.0f; // Trở kháng vô cùng khi hở mạch
    data.rawConductance_uS = 0.0f;
    data.conductance_uS    = 0.0f;
    data.valid             = false;
    return data;
  }

  // Ngắn mạch hoặc bão hòa rail trên của op-amp (> 3.10V)
  if (rawVoltage_mV > GSR_HARDWARE_SATURATED_MV) {
    status_ = GSRStatus::SATURATED;
    voltageFilter_.reset();
    conductanceFilter_.reset();
    data.voltage           = rawVoltage;
    data.voltage_mV        = rawVoltage_mV;
    data.status            = status_;
    data.resistance        = 0.0f;
    data.rawConductance_uS = 0.0f;
    data.conductance_uS    = 0.0f;
    data.valid             = false;
    return data;
  }

  // 3. Lọc EMA làm mịn điện áp: triệt tiêu nhiễu ADC, gai điện áp nguồn và rung giật
  data.voltage = voltageFilter_.update(rawVoltage);
  data.voltage_mV = static_cast<uint32_t>(data.voltage * 1000.0f + 0.5f);

  // 4. Tính toán trở kháng da R_skin và độ dẫn Conductance G (µS)
  // Theo mạch Grove GSR v1.2: ngõ ra op-amp tỉ lệ thuận với độ dẫn da.
  // R_skin = 25000 * (3.3 - V) / (V - 0.10)
  const float vSpan = data.voltage - 0.10f;
  if (vSpan > 0.01f && data.voltage < 3.28f) {
    data.resistance = (25000.0f * (3.3f - data.voltage)) / vSpan;
    if (data.resistance > 0.0f) {
      const float rawConductance = 1000000.0f / data.resistance;
      data.rawConductance_uS = rawConductance;
      data.conductance_uS = conductanceFilter_.update(rawConductance);
    }
  }

  const unsigned long now = millis();

  // 4. Thiết lập Baseline phiên đo động (Dynamic Session Baseline)
  // Khi bắt đầu đeo điện cực hợp lệ, kích hoạt cửa sổ hiệu chuẩn 5 giây đầu
  if (!isCalibrating_ && baselineMv_ == 0.0f) {
    isCalibrating_ = true;
    calibrationStartMs_ = now;
    calibMvSum_ = 0;
    calibSampleCount_ = 0;
  }

  if (isCalibrating_) {
    calibMvSum_ += data.voltage_mV;
    calibSampleCount_++;
    status_ = GSRStatus::CALIBRATING;
    data.status = status_;

    if (now - calibrationStartMs_ >= GSR_CALIBRATION_TIME_MS && calibSampleCount_ > 0) {
      baselineMv_ = static_cast<float>(calibMvSum_) / static_cast<float>(calibSampleCount_);
      const float baseV = baselineMv_ / 1000.0f;
      const float baseSpan = baseV - 0.10f;
      if (baseSpan > 0.01f && baseV < 3.28f) {
        float baseR = (25000.0f * (3.3f - baseV)) / baseSpan;
        if (baseR > 0.0f) baselineConductance_ = 1000000.0f / baseR;
      }
      isCalibrating_ = false;
      status_ = GSRStatus::VALID;
      Serial.printf("[GSR] Đã xác lập Baseline phiên đo: %.1f mV | %.2f µS\n",
                    baselineMv_, baselineConductance_);
    } else {
      // Đang trong thời gian hiệu chuẩn, dữ liệu chưa coi là hoàn tất phiên
      data.valid = false;
      return data;
    }
  }

  // 5. Tính toán các chỉ số so với baseline
  status_ = GSRStatus::VALID;
  data.status = status_;
  data.baselineVoltage_mV     = baselineMv_;
  data.baselineConductance_uS = baselineConductance_;
  data.deltaConductance_uS    = data.conductance_uS - baselineConductance_;

  if (baselineConductance_ > 0.05f) {
    data.percentChange = (data.deltaConductance_uS / baselineConductance_) * 100.0f;
  }

  // Cảnh báo vượt ngưỡng kích thích giao cảm (SCR Event: tăng > 2 µS so với baseline)
  data.thresholdExceeded = (data.deltaConductance_uS > 2.0f);
  data.valid = true;
  return data;
}

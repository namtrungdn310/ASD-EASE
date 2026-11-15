#include "GSRSensor.h"
#include <esp_timer.h>
#include <cmath>
#include <limits>

Availability GSRSensor::begin() {
  pin_ = PIN_GSR_ADC;
  if (pin_ < 0) { status_ = GSRStatus::ERROR; return Availability::ERROR; }
  analogReadResolution(GSR_ADC_RESOLUTION);
  analogSetPinAttenuation(pin_, ADC_11db);
  pinMode(pin_, INPUT);
  (void)analogRead(pin_);
  // Cùng mẫu ADC raw được đổi sang mV, không đọc lại một mẫu khác để quy đổi.
  static_assert(PIN_GSR_ADC == 7 && GSR_ADC_RESOLUTION == 12,
                "Update ADC unit/channel/calibration when changing hardware");
  const auto calibration = esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_12,
      ADC_WIDTH_BIT_12, 1100, &adcCalibration_);
  voltageCalibrated_ = calibration == ESP_ADC_CAL_VAL_EFUSE_TP_FIT ||
      calibration == ESP_ADC_CAL_VAL_EFUSE_TP || calibration == ESP_ADC_CAL_VAL_EFUSE_VREF;
  ready_ = true;
  status_ = GSRStatus::CALIBRATING;
  resetBaseline();
  Serial.printf("[GSR] GPIO%d ADC12/11dB | ADC-cal=%u | conductance-cal=%u\n",
      pin_, unsigned(voltageCalibrated_), unsigned(GSR_CONDUCTANCE_CALIBRATED));
  return Availability::READY;
}

void GSRSensor::resetBaseline() {
  baseline_.reset();
  voltageFilter_.reset();
  conductanceFilter_.reset();
}

GSRData GSRSensor::read() {
  GSRData data{};
  const float unavailable = std::numeric_limits<float>::quiet_NaN();
  data.rawVoltage = data.voltage = unavailable;
  data.resistance = data.rawConductance_uS = data.conductance_uS = unavailable;
  data.baselineConductance_uS = data.deltaConductance_uS = data.percentChange = unavailable;
  data.voltageCalibrated = voltageCalibrated_;
  if (!ready_ || pin_ < 0) { data.status = GSRStatus::ERROR; return data; }

  uint32_t sum = 0;
  bool clipped = false, rail = false;
  for (unsigned i = 0; i < GSR_AVERAGING_SAMPLES; ++i) {
    const uint32_t raw = analogRead(pin_);
    sum += raw;
    rail = rail || raw == 0 || raw >= GSR_ADC_MAX_VALUE;
    clipped = clipped || raw >= GSR_ADC_MAX_VALUE;
  }
  data.rawADC = static_cast<uint16_t>((sum + GSR_AVERAGING_SAMPLES / 2) / GSR_AVERAGING_SAMPLES);
  data.sampleUpdatedAtMs = millis();
  data.sampleMonotonicMs = static_cast<uint64_t>(esp_timer_get_time()) / 1000;
  data.hasSampleTimestamp = true;
  quality_.add(data.sampleMonotonicMs, rail);
  if (clipped) {
    resetBaseline();
    status_ = data.status = GSRStatus::SATURATED;
    return data;
  }
  if (!voltageCalibrated_) {
    // Có ADC raw; không dựng mV/µS từ Vref mặc định chưa kiểm chứng.
    status_ = data.status = GSRStatus::VALID;
    return data;
  }
  data.rawVoltage_mV = esp_adc_cal_raw_to_voltage(data.rawADC, &adcCalibration_);
  data.rawVoltage = data.rawVoltage_mV / 1000.0f;
  if (data.rawVoltage_mV < GSR_HARDWARE_OPEN_MV ||
      data.rawVoltage_mV >= GSR_HARDWARE_SATURATED_MV) {
    status_ = data.rawVoltage_mV < GSR_HARDWARE_OPEN_MV ?
        GSRStatus::DISCONNECTED : GSRStatus::SATURATED;
    data.status = status_;
    resetBaseline();
    return data;
  }

  data.voltage = voltageFilter_.update(data.rawVoltage);
  data.voltage_mV = static_cast<uint32_t>(std::lround(data.voltage * 1000));
  data.rawConductance_uS = asd::gsrConductance(data.rawVoltage,
      GSR_CONDUCTANCE_CALIBRATED, GSR_MODEL_SUPPLY_V, GSR_MODEL_OFFSET_V,
      GSR_MODEL_RESISTOR_OHMS);
  data.conductanceCalibrated = std::isfinite(data.rawConductance_uS);
  if (data.conductanceCalibrated) {
    data.resistance = 1000000.0f / data.rawConductance_uS;
    data.conductance_uS = conductanceFilter_.update(data.rawConductance_uS);
  }
  if (!baseline_.update(data.sampleMonotonicMs, data.rawVoltage_mV)) {
    status_ = data.status = GSRStatus::CALIBRATING;
    return data;
  }
  data.baselineVoltage_mV = baseline_.millivolts();
  data.baselineConductance_uS = asd::gsrConductance(data.baselineVoltage_mV / 1000,
      data.conductanceCalibrated, GSR_MODEL_SUPPLY_V, GSR_MODEL_OFFSET_V,
      GSR_MODEL_RESISTOR_OHMS);
  if (std::isfinite(data.baselineConductance_uS) && data.baselineConductance_uS > .05f) {
    data.deltaConductance_uS = data.conductance_uS - data.baselineConductance_uS;
    data.percentChange = data.deltaConductance_uS / data.baselineConductance_uS * 100;
  }
  data.thresholdExceeded = false; // Không tự gắn nhãn SCR bằng một ngưỡng µS.
  status_ = data.status = GSRStatus::VALID;
  data.valid = true;
  return data;
}

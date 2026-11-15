#pragma once
#include <cstdint>
enum esp_adc_cal_value_t {
  ESP_ADC_CAL_VAL_EFUSE_VREF, ESP_ADC_CAL_VAL_EFUSE_TP,
  ESP_ADC_CAL_VAL_DEFAULT_VREF, ESP_ADC_CAL_VAL_EFUSE_TP_FIT
};
constexpr int ADC_UNIT_1 = 1, ADC_ATTEN_DB_12 = 3, ADC_WIDTH_BIT_12 = 12;
struct esp_adc_cal_characteristics_t {};
inline esp_adc_cal_value_t fakeCalibration = ESP_ADC_CAL_VAL_EFUSE_TP_FIT;
inline esp_adc_cal_value_t esp_adc_cal_characterize(int, int, int, int,
    esp_adc_cal_characteristics_t*) { return fakeCalibration; }
inline uint32_t esp_adc_cal_raw_to_voltage(uint32_t raw, const esp_adc_cal_characteristics_t*) {
  // Hàm chuyển đổi giả để chứng minh driver dùng nó, không dùng raw*3300/4095.
  return raw;
}

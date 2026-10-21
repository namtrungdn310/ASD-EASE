#pragma once
#include <Arduino.h>
#include "common_types.h"

// =============================================================================
// board_config.h — Unified Hardware & Sensor Configuration
// =============================================================================
// Tất cả hằng số phần cứng, chân GPIO, địa chỉ I2C, và cấu hình cảm biến
// đều nằm ở đây. Mỗi sensor header chỉ cần #include "board_config.h".
// =============================================================================

// ── Firmware / Device Identity ───────────────────────────────────────────────
#define ASD_SCHEMA_VERSION   "1.0"
#define ASD_DEVICE_ID        "ASD-ESP32S3-SUPERMINI"

#ifndef FIRMWARE_VERSION
  #define FIRMWARE_VERSION "0.2.0"
#endif
#define ASD_FIRMWARE_VERSION FIRMWARE_VERSION

// ── Shared Enums ──────────────────────────────────────────────────────────────

enum class GSRStatus {
  DISCONNECTED,   // Điện áp < 0.15V: hở mạch, chưa đeo điện cực (LM324 lower rail)
  SATURATED,      // Điện áp > 3.10V: ngắn mạch / bão hòa rail trên
  CALIBRATING,    // Đang lấy mẫu thiết lập baseline ban đầu (3-5 giây đầu sau khi đeo)
  VALID,          // Dữ liệu hợp lệ, nằm trong dải sinh lý
  ERROR           // Lỗi phần cứng hoặc ADC
};

enum class PPGStatus {
  DISCONNECTED,    // Không tìm thấy chip I2C hoặc mất bus
  NO_FINGER,       // IR < 50000: chưa đặt ngón tay lên cảm biến
  PULSE_ACQUIRING, // Đã đặt ngón tay, đang thu thập và lọc xung mạch (chờ nhịp ổn định)
  VALID,           // Nhịp tim và SpO2 đo được ổn định
  ERROR            // Lỗi giao tiếp I2C
};

enum class IMUStatus {
  DISCONNECTED,   // Không phản hồi địa chỉ I2C hoặc mất kết nối
  CALIBRATING,    // Đang lấy mẫu offset tĩnh
  VALID,          // Đọc dữ liệu 6 trục và nhiệt độ bình thường
  ERROR           // Lỗi bus hoặc dữ liệu bất thường
};

// ── GPIO Pin Assignments (ESP32-S3 Super Mini) ───────────────────────────────
//   Bus 0 (Wire)  — MAX30102: SDA = GPIO8,  SCL = GPIO9
//   Bus 1 (Wire1) — MPU6050:  SDA = GPIO10, SCL = GPIO11 (Khởi tạo riêng biệt chống nghẽn)
//   GSR ADC: GPIO4 theo cấu hình hiện tại; wiring chưa được xác minh.
constexpr int PIN_MAX30102_SDA = 8;
constexpr int PIN_MAX30102_SCL = 9;

constexpr int PIN_MPU6050_SDA  = 10;
constexpr int PIN_MPU6050_SCL  = 11;

constexpr int PIN_GSR_ADC      = 4;

// Giữ alias tương thích
constexpr int PIN_I2C_SDA      = PIN_MAX30102_SDA;
constexpr int PIN_I2C_SCL      = PIN_MAX30102_SCL;

// ── I2C Bus Configuration ────────────────────────────────────────────────────
constexpr uint8_t  I2C_ADDR_MAX30102 = 0x57;   // Fixed by silicon
constexpr uint8_t  I2C_ADDR_MPU6050  = 0x68;   // AD0 → GND  (0x69 nếu AD0 → VCC/hở)
constexpr uint32_t I2C_CLOCK_HZ      = 100000;  // 100 kHz Standard Mode (chống nhiễu, cực kỳ ổn định)
constexpr uint32_t I2C_TIMEOUT_MS    = 50;      // 50 ms timeout chống treo bus
constexpr unsigned long I2C_RETRY_INTERVAL_MS = 3000UL; // Chu kỳ tự động thử kết nối lại nếu sensor rớt bus (3s)

// ── Main Loop Timing ─────────────────────────────────────────────────────────
constexpr unsigned long LOOP_INTERVAL_MS = 10;   // 100 Hz base loop

// ── MAX30102 (PPG / Heart-Rate / SpO2) ───────────────────────────────────────
constexpr unsigned PPG_RAW_SAMPLE_RATE_HZ = 100;
constexpr uint8_t  PPG_SAMPLE_AVERAGE     = 2;    // On-chip averaging -> 50 Hz effective
constexpr unsigned PPG_SAMPLE_RATE_HZ     = PPG_RAW_SAMPLE_RATE_HZ;
constexpr unsigned PPG_EFFECTIVE_RATE_HZ  = PPG_RAW_SAMPLE_RATE_HZ / PPG_SAMPLE_AVERAGE;
constexpr unsigned long PPG_SAMPLE_PERIOD_MS = 1000UL / PPG_EFFECTIVE_RATE_HZ;
constexpr uint8_t  PPG_LED_BRIGHTNESS     = 0x1F; // ~6.2 mA
constexpr uint8_t  PPG_LED_MODE           = 2;    // 2 = Red + IR (SpO2 mode)
constexpr uint16_t PPG_PULSE_WIDTH        = 411;  // µs -> 18-bit ADC resolution
constexpr uint16_t PPG_ADC_RANGE          = 4096; // nA full-scale

// Ngưỡng tín hiệu & sinh lý MAX30102
constexpr uint32_t PPG_IR_FINGER_THRESHOLD = 50000UL; // Raw IR tối thiểu để xác nhận tiếp xúc da
constexpr float    PPG_AC_MIN_AMPLITUDE    = 50.0f;   // Biên độ AC tối thiểu để bắt đỉnh sóng mạch
constexpr float    HR_MIN_PHYSIOLOGICAL    = 40.0f;   // BPM thấp nhất hợp lệ
constexpr float    HR_MAX_PHYSIOLOGICAL    = 200.0f;  // BPM cao nhất hợp lệ
constexpr float    SPO2_MIN_PHYSIOLOGICAL  = 70.0f;   // % SpO2 tối thiểu hợp lệ
constexpr float    SPO2_MAX_PHYSIOLOGICAL  = 100.0f;  // % SpO2 tối đa hợp lệ

// Cấu hình bộ lọc EMA cho PPG
constexpr float    PPG_EMA_ALPHA_HR        = 0.15f;   // Lọc nhịp tim BPM (làm mượt êm dịu, triệt tiêu nhảy số)
constexpr float    PPG_EMA_ALPHA_SPO2      = 0.10f;   // Lọc SpO2 (%) chống dao động quang học

// ── MPU6050 (6-Axis IMU) ────────────────────────────────────────────────────
constexpr unsigned IMU_SAMPLE_RATE_HZ = 50;
constexpr uint8_t  IMU_ACCEL_RANGE    = 0;      // 0 = ±2 g (16384 LSB/g)
constexpr uint8_t  IMU_GYRO_RANGE     = 0;      // 0 = ±250 °/s (131 LSB/(°/s))
constexpr uint8_t  IMU_FILTER_BW      = 3;      // 3 = 44 Hz bandwidth

// Cấu hình bộ lọc EMA cho IMU
constexpr float    IMU_EMA_ALPHA_ACCEL = 0.25f;  // Lọc gia tốc 3 trục (m/s²), triệt rung giật nhiễu
constexpr float    IMU_EMA_ALPHA_GYRO  = 0.25f;  // Lọc vận tốc góc 3 trục (°/s), triệt tiêu nhiễu phiêu

// ── GSR (Galvanic Skin Response) ─────────────────────────────────────────────
constexpr unsigned GSR_SAMPLE_RATE_HZ       = 20;
constexpr uint8_t  GSR_ADC_RESOLUTION       = 12;     // ESP32-S3 12-bit ADC
constexpr uint16_t GSR_ADC_MAX_VALUE        = 4095;   // 2^12 - 1
constexpr uint16_t GSR_ADC_FULL_SCALE_MV    = 3300;   // Quy đổi tuyến tính theo mức 3.3 V
constexpr unsigned GSR_AVERAGING_SAMPLES    = 8;      // Software oversampling
constexpr uint32_t GSR_CALIBRATION_TIME_MS  = 5000UL; // 5 giây lấy mẫu thiết lập baseline động sau khi đeo

// Cấu hình bộ lọc EMA cho GSR
constexpr float    GSR_EMA_ALPHA_VOLTAGE     = 0.20f;  // Lọc điện áp ADC, triệt tiêu nhiễu lưới 50Hz & rung ngón
constexpr float    GSR_EMA_ALPHA_CONDUCTANCE = 0.20f;  // Lọc độ dẫn da Conductance (µS)

// Phân tầng ngưỡng GSR:
// 1. Giới hạn điện phần cứng (Hardware Electrical Limits)
//    - LM324 single-supply có ngõ ra bão hòa mức thấp Vol ≈ 0.05V - 0.15V khi hở mạch (R_skin = vô cùng)
//    - Do đó, điện áp dưới 150 mV là trạng thái CHƯA ĐEO ĐIỆN CỰC / HỞ MẠCH (DISCONNECTED)
constexpr uint32_t GSR_HARDWARE_OPEN_MV      = 150;    // < 150 mV: Hở mạch (LM324 low rail)
constexpr uint32_t GSR_HARDWARE_SATURATED_MV = 3100;   // > 3100 mV: Ngắn mạch / Bão hòa rail cao

// 2. Ngưỡng sinh lý độ dẫn da (Physiological Limits for Human EDA)
//    - Conductance người bình thường: 1.0 µS đến 30.0 µS (tương đương trở kháng ~33 kΩ đến 1 MΩ)
constexpr float GSR_CONDUCTANCE_MIN_US = 0.5f;   // µS (dưới mức này xem như tiếp xúc kém)
constexpr float GSR_CONDUCTANCE_MAX_US = 50.0f;  // µS (trên mức này xem như mồ hôi ướt đẫm hoặc chập cực)

// ── Output Formatting & Timing ───────────────────────────────────────────────
enum class OutputFormat {
  PRETTY_TEXT,   // Định dạng văn bản phân tách 3 cảm biến rõ ràng, xuống dòng dễ nhìn trên Serial Monitor
  PRETTY_JSON    // Gói dữ liệu JSON định dạng đẹp (thụt lề, xuống dòng từng trường)
};
constexpr OutputFormat DEFAULT_OUTPUT_FORMAT = OutputFormat::PRETTY_TEXT;
constexpr unsigned long DEFAULT_OUTPUT_INTERVAL_MS = 1000UL; // Chu kỳ xuất gói dữ liệu (1000ms = 1 Hz)

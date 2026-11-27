#pragma once
#include <Arduino.h>
#include "common_types.h"

// =============================================================================
// board_config.h — Cấu hình phần cứng/cảm biến dùng chung
// =============================================================================
// Tất cả hằng số phần cứng, chân GPIO, địa chỉ I2C, và cấu hình cảm biến
// đều nằm ở đây. Mỗi sensor header chỉ cần #include "board_config.h".
// =============================================================================

// ── Phiên bản firmware và mã thiết bị ───────────────────────────────────────────────
#define ASD_SCHEMA_VERSION "1.2"
#define ASD_DEVICE_ID "ESP32-001"

// Bản HR đang được đánh giá trên cổ tay; native build có thể tắt tracker để đối chiếu.
#ifndef ASD_PPG_TRACKER_ENABLED
#define ASD_PPG_TRACKER_ENABLED 1
#endif

#ifndef FIRMWARE_VERSION
#if ASD_PPG_TRACKER_ENABLED
#define FIRMWARE_VERSION "0.4.7-rr-average-tracker"
#else
#define FIRMWARE_VERSION "0.4.7-native-baseline"
#endif
#endif
#define ASD_FIRMWARE_VERSION FIRMWARE_VERSION

enum class GSRStatus {
  DISCONNECTED, // Dưới ngưỡng điện áp kỹ thuật; chưa chứng minh tình trạng tiếp xúc
  SATURATED, // ADC chạm rail hoặc điện áp ngoài vùng đọc đã cấu hình
  CALIBRATING, // Chờ cửa sổ điện áp nền ổn định
  VALID, // Dữ liệu được driver chấp nhận, chưa chứng minh độ chính xác sinh lý
  ERROR  // Lỗi phần cứng hoặc ADC
};

enum class PPGStatus {
  DISCONNECTED, // Không tìm thấy chip I2C hoặc mất bus
  NO_FINGER,    // IR chưa vượt ngưỡng tiếp xúc; tên giữ tương thích cổ tay/ngón tay
  PULSE_ACQUIRING, // Đã đặt ngón tay, đang thu thập và lọc xung mạch (chờ nhịp
                   // ổn định)
  VALID, // Driver đủ điều kiện nhịp tim; chưa chứng minh SpO2 chính xác
  ERROR  // Lỗi giao tiếp I2C
};

enum class IMUStatus {
  DISCONNECTED, // Không phản hồi địa chỉ I2C hoặc mất kết nối
  CALIBRATING,  // Đang lấy mẫu offset tĩnh
  VALID,        // Đọc dữ liệu 6 trục và nhiệt độ bình thường
  ERROR         // Lỗi bus hoặc dữ liệu bất thường
};

// ── Chân GPIO được cấu hình (ESP32-S3 Super Mini) ───────────────────────────────
//   Bus 0 (Wire)  — MAX30102: SDA = GPIO8,  SCL = GPIO9
//   Bus 1 (Wire1) — MPU6050:  SDA = GPIO10, SCL = GPIO11 (Khởi tạo riêng biệt chống nghẽn)
//   ADC1_CH6      — GSR:      ADC = GPIO7
constexpr int PIN_MAX30102_SDA = 8;
constexpr int PIN_MAX30102_SCL = 9;

constexpr int PIN_MPU6050_SDA = 10;
constexpr int PIN_MPU6050_SCL = 11;

constexpr int PIN_GSR_ADC = 7;

// Giữ alias tương thích
constexpr int PIN_I2C_SDA = PIN_MAX30102_SDA;
constexpr int PIN_I2C_SCL = PIN_MAX30102_SCL;

// ── Cấu hình bus I2C ────────────────────────────────────────────────────
constexpr uint8_t I2C_ADDR_MAX30102 = 0x57; // Địa chỉ cố định của chip
constexpr uint8_t I2C_ADDR_MPU6050 = 0x68; // AD0 → GND  (driver cũng thử 0x69; nối AD0 theo sơ đồ mô-đun)
constexpr uint32_t I2C_CLOCK_HZ =
    100000; // Standard Mode; tốc độ/độ ổn định thực cần đo
constexpr uint32_t I2C_TIMEOUT_MS = 50; // 50 ms timeout chống treo bus
constexpr unsigned long I2C_RETRY_INTERVAL_MS =
    3000UL; // Chu kỳ tự động thử kết nối lại nếu sensor rớt bus (3s)

// ── Chu kỳ vòng lặp chính ─────────────────────────────────────────────────────────
constexpr unsigned long LOOP_INTERVAL_MS = 10; // Chu kỳ mục tiêu 100 Hz, cần đo nhịp thực

// ── MAX30102 (PPG và nhịp tim; chưa ước tính SpO2) ───────────────────────
constexpr unsigned PPG_RAW_SAMPLE_RATE_HZ = 200;
constexpr uint8_t PPG_SAMPLE_AVERAGE = 4;
constexpr unsigned PPG_SAMPLE_RATE_HZ     = PPG_RAW_SAMPLE_RATE_HZ;
constexpr unsigned PPG_EFFECTIVE_RATE_HZ  = PPG_RAW_SAMPLE_RATE_HZ / PPG_SAMPLE_AVERAGE; // 50 Hz
constexpr unsigned long PPG_SAMPLE_PERIOD_MS = 1000UL / PPG_EFFECTIVE_RATE_HZ; // 20 ms
constexpr uint8_t PPG_LED_BRIGHTNESS = 0x32; // ~10mA danh định, giữ cấu hình 0.3.23 đã đo
constexpr uint8_t  PPG_LED_MODE           = 2;    // RED + IR để đối chiếu tín hiệu nhịp tim
constexpr uint16_t PPG_PULSE_WIDTH        = 411;  // µs, cấu hình ADC 18 bit
constexpr uint16_t PPG_ADC_RANGE          = 4096; // Toàn thang, nA

// Ngưỡng tín hiệu & sinh lý MAX30102
constexpr uint32_t PPG_IR_FINGER_THRESHOLD =
    4500UL; // Cao hơn nền hở thực tế (~2300..2550) để không báo nhầm contact=1 khi chưa đặt tay
constexpr uint32_t PPG_IR_CONTACT_OFF = 3200UL; // Hysteresis ngắt tiếp xúc ngay khi nhấc tay khỏi cảm biến
constexpr uint32_t PPG_CONTACT_SETTLE_MS = 1000UL; // Chờ DC ổn định trước bắt nhịp
// Cổ tay: khi thí nghiệm trên bàn/mạch rời, tắt guard cổ tay để MAX30102 bắt nhịp độc lập với IMU.
#ifndef ASD_PPG_WRIST_MOTION_GUARD
#define ASD_PPG_WRIST_MOTION_GUARD 0
#endif
// Bộ lọc ở processing/ppg_rate.h; HR chạy bằng processing/ppg_cycle_tracker.h.
// Không khai báo thêm các núm chỉnh ở đây khi thuật toán không đọc chúng.
constexpr float HR_MIN_PHYSIOLOGICAL = 40.0f;    // BPM thấp nhất hợp lệ
constexpr float HR_MAX_PHYSIOLOGICAL = 200.0f;   // BPM cao nhất hợp lệ

// ── MPU6050 (IMU sáu trục) ────────────────────────────────────────────────────
constexpr unsigned IMU_SAMPLE_RATE_HZ = 50;
constexpr uint8_t IMU_ACCEL_RANGE = 0; // 0: thang đo ±2 g, 16384 LSB/g
constexpr uint8_t IMU_GYRO_RANGE = 0;  // 0: thang đo ±250 °/s, 131 LSB/(°/s)
constexpr uint8_t IMU_FILTER_BW = 5;   // 10 Hz trước FIFO 50 Hz; giảm alias, cần đo đáp ứng thật
constexpr bool IMU_AUTO_GYRO_BIAS = true; // Một lần/khởi tạo, cần khoảng 2 giây đứng yên

// Cấu hình bộ lọc EMA cho IMU
constexpr float IMU_EMA_ALPHA_ACCEL =
    1.0f; // Chip đã lọc 10 Hz; giữ đáp ứng, không thêm tầng EMA 2.3 Hz
constexpr float IMU_EMA_ALPHA_GYRO =
    1.0f; // Có thể giảm riêng cho hiển thị sau khi đo; raw luôn tách riêng

// ── GSR (tín hiệu điện da) ─────────────────────────────────────────────
constexpr unsigned GSR_SAMPLE_RATE_HZ = 20;
constexpr uint8_t GSR_ADC_RESOLUTION = 12;   // Cấu hình ADC 12 bit
constexpr uint16_t GSR_ADC_MAX_VALUE = 4095; // 2^12 - 1
constexpr bool GSR_CONDUCTANCE_CALIBRATED = false; // Chỉ bật sau kiểm chứng mạch bằng điện trở chuẩn
constexpr float GSR_MODEL_SUPPLY_V = 3.3f;
constexpr float GSR_MODEL_OFFSET_V = 0.10f;
constexpr float GSR_MODEL_RESISTOR_OHMS = 25000.0f;
constexpr unsigned GSR_AVERAGING_SAMPLES = 8; // Trung bình nhiều lần đọc bằng phần mềm
constexpr uint32_t GSR_CALIBRATION_TIME_MS = 5000UL; // Độ dài cửa sổ, sau 1 giây chờ

// Cấu hình bộ lọc EMA cho GSR
constexpr float GSR_EMA_ALPHA_VOLTAGE =
    0.20f; // Làm mượt ADC; không phải bộ lọc riêng cho nhiễu 50 Hz
constexpr float GSR_EMA_ALPHA_CONDUCTANCE =
    0.20f; // Lọc độ dẫn da Conductance (µS)

// Ngưỡng điện áp phát triển, cần đối chiếu biến trở/module thực.
// Không dùng riêng mức điện áp để kết luận trạng thái da hay ngắn mạch.
constexpr uint32_t GSR_HARDWARE_OPEN_MV =
    150; // Dưới vùng điện áp đang dùng
constexpr uint32_t GSR_HARDWARE_SATURATED_MV =
    3100; // Giới hạn vùng đọc ADC; chạm 4095 cũng coi là bão hòa

// ── Định dạng và chu kỳ xuất dữ liệu ───────────────────────────────────────────────
enum class OutputFormat {
  PRETTY_TEXT, // Định dạng văn bản phân tách 3 cảm biến rõ ràng, xuống dòng dễ
               // nhìn trên Serial Monitor
  PRETTY_JSON // Gói dữ liệu JSON định dạng đẹp (thụt lề, xuống dòng từng
              // trường)
};
constexpr OutputFormat DEFAULT_OUTPUT_FORMAT = OutputFormat::PRETTY_TEXT;
constexpr unsigned long DEFAULT_OUTPUT_INTERVAL_MS =
    1000UL; // Chu kỳ xuất gói dữ liệu (1000ms = 1 Hz)

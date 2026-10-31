#pragma once
#include "board_config.h"
#include "EMA.h"

// =============================================================================
// MPU6050 — gia tốc/vận tốc góc sáu trục
// =============================================================================

struct MPU6050Data {
  // Giá trị thô (Raw - trước lọc EMA)
  float     rawAx = 0.0f, rawAy = 0.0f, rawAz = 0.0f;             // Gia tốc thô 3 trục (m/s²)
  float     rawGx = 0.0f, rawGy = 0.0f, rawGz = 0.0f;             // Vận tốc góc thô 3 trục (rad/s)
  float     rawGx_deg = 0.0f, rawGy_deg = 0.0f, rawGz_deg = 0.0f; // Vận tốc góc thô 3 trục (°/s)

  // Giá trị mượt (Filtered - sau lọc EMA)
  float     ax = 0.0f, ay = 0.0f, az = 0.0f;             // Gia tốc 3 trục sau EMA (m/s²)
  float     accelMagnitude = 0.0f;                        // Độ lớn vector |a| (m/s²)
  float     gx = 0.0f, gy = 0.0f, gz = 0.0f;             // Vận tốc góc 3 trục sau EMA (rad/s)
  float     gx_deg = 0.0f, gy_deg = 0.0f, gz_deg = 0.0f; // Vận tốc góc 3 trục sau EMA (°/s)
  float     temperature = 0.0f;                            // Nhiệt độ chip (°C)
  IMUStatus status = IMUStatus::DISCONNECTED;             // Trạng thái hoạt động
  uint8_t   whoAmI = 0x00;                                // Mã chip ID (WHO_AM_I)
  bool      valid  = false;                               // Cờ hợp lệ
};

class TwoWire;

class MPU6050Sensor {
 public:
  Availability begin(TwoWire* wirePort = nullptr);
  MPU6050Data  read();
  bool isReady() const { return ready_; }
  uint8_t getAddress() const { return i2cAddr_; }
  uint8_t getWhoAmI() const { return whoAmI_; }
  IMUStatus getStatus() const { return status_; }
  void resetFilters();

 private:
  bool writeRegister(uint8_t reg, uint8_t value);
  bool readRegisters(uint8_t reg, uint8_t* buffer, size_t len);

  TwoWire*      wire_              = nullptr;
  bool          ready_             = false;
  uint8_t       i2cAddr_           = I2C_ADDR_MPU6050;
  uint8_t       whoAmI_            = 0x00;
  IMUStatus     status_            = IMUStatus::DISCONNECTED;
  uint32_t      consecutiveErrors_ = 0;
  unsigned long lastRetryMs_       = 0;

  // Bộ lọc EMA cho 3 trục gia tốc và 3 trục vận tốc góc
  EMA           axFilter_{IMU_EMA_ALPHA_ACCEL};
  EMA           ayFilter_{IMU_EMA_ALPHA_ACCEL};
  EMA           azFilter_{IMU_EMA_ALPHA_ACCEL};

  EMA           gxFilter_{IMU_EMA_ALPHA_GYRO};
  EMA           gyFilter_{IMU_EMA_ALPHA_GYRO};
  EMA           gzFilter_{IMU_EMA_ALPHA_GYRO};
};

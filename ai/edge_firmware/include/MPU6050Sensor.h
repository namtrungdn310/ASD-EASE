#pragma once
#include "board_config.h"
#include "processing/measurement_quality.h"
#include "EMA.h"
#include "processing/movement_score.h"
#include "processing/sensor_math.h"
#include "processing/imu_fifo.h"

// =============================================================================
// MPU6050 — gia tốc/vận tốc góc sáu trục
// =============================================================================

struct MPU6050Data {
  uint64_t sampleMonotonicMs = 0;
  uint32_t sampleUpdatedAtMs = 0;
  bool hasSampleTimestamp = false;
  uint32_t newSamples = 0;
  bool gyroCalibrated = false;
  float movementScore = 0.0f;
  bool movementValid = false;
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

struct ImuAcquisitionStats {
  uint32_t samples = 0, ioErrors = 0, overflowEvents = 0, gaps = 0, clipped = 0;
};

class MPU6050Sensor {
 public:
  using SampleObserver=void (*)(const MPU6050Data&);
  void setSampleObserver(SampleObserver observer){observer_=observer;}
  Availability begin(TwoWire* wirePort = nullptr);
  MPU6050Data  read();
  bool isReady() const { return ready_; }
  uint8_t getAddress() const { return i2cAddr_; }
  uint8_t getWhoAmI() const { return whoAmI_; }
  IMUStatus getStatus() const { return status_; }
  void resetFilters();
  asd::MeasurementQuality accelerationQuality(uint64_t now) const { return accelerationQuality_.evaluate(now, 50); }
  asd::MeasurementQuality rotationQuality(uint64_t now) const { return rotationQuality_.evaluate(now, 50); }
  const ImuAcquisitionStats& acquisitionStats() const { return stats_; }
  std::array<float, 3> gyroOffsets() const { return gyroBias_.offsets(); }

 private:
  bool writeRegister(uint8_t reg, uint8_t value);
  bool readRegisters(uint8_t reg, uint8_t* buffer, size_t len);
  bool configure();
  bool resetFifo();
  void fail();
  MPU6050Data process(const asd::ImuRawSample& raw, uint64_t measured);

  SampleObserver observer_=nullptr;
  TwoWire*      wire_              = nullptr;
  bool          ready_             = false;
  uint8_t       i2cAddr_           = I2C_ADDR_MPU6050;
  uint8_t       whoAmI_            = 0x00;
  IMUStatus     status_            = IMUStatus::DISCONNECTED;
  unsigned long lastRetryMs_       = 0;
  asd::MovementScoreEstimator movement_;
  asd::GyroBias gyroBias_;
  ImuAcquisitionStats stats_{};
  asd::QualityWindow accelerationQuality_, rotationQuality_;
  MPU6050Data latest_{};
  asd::SampleClock clock_;
  uint32_t stageStarted_ = 0;
  uint32_t lastFifoMs_ = 0;
  uint8_t initStage_ = 0;

  // Bộ lọc EMA cho 3 trục gia tốc và 3 trục vận tốc góc
  EMA           axFilter_{IMU_EMA_ALPHA_ACCEL};
  EMA           ayFilter_{IMU_EMA_ALPHA_ACCEL};
  EMA           azFilter_{IMU_EMA_ALPHA_ACCEL};

  EMA           gxFilter_{IMU_EMA_ALPHA_GYRO};
  EMA           gyFilter_{IMU_EMA_ALPHA_GYRO};
  EMA           gzFilter_{IMU_EMA_ALPHA_GYRO};
};

#include "MPU6050Sensor.h"
#include <Wire.h>
#include <cmath>


static constexpr uint8_t REG_SMPLRT_DIV   = 0x19;
static constexpr uint8_t REG_CONFIG       = 0x1A;
static constexpr uint8_t REG_GYRO_CONFIG  = 0x1B;
static constexpr uint8_t REG_ACCEL_CONFIG = 0x1C;
static constexpr uint8_t REG_ACCEL_XOUT_H = 0x3B;
static constexpr uint8_t REG_PWR_MGMT_1   = 0x6B;
static constexpr uint8_t REG_WHO_AM_I     = 0x75;

bool MPU6050Sensor::writeRegister(uint8_t reg, uint8_t value) {
  if (wire_ == nullptr) wire_ = &Wire1;
  wire_->beginTransmission(i2cAddr_);
  wire_->write(reg);
  wire_->write(value);
  return (wire_->endTransmission() == 0);
}

bool MPU6050Sensor::readRegisters(uint8_t reg, uint8_t* buffer, size_t len) {
  if (wire_ == nullptr) wire_ = &Wire1;
  wire_->beginTransmission(i2cAddr_);
  wire_->write(reg);
  
  if (wire_->endTransmission(false) != 0) {
    return false;
  }

  uint8_t bytesRead = wire_->requestFrom(i2cAddr_, static_cast<uint8_t>(len));
  if (bytesRead != len) return false;

  for (size_t i = 0; i < len; ++i) {
    buffer[i] = wire_->read();
  }
  return true;
}

// =============================================================================
Availability MPU6050Sensor::begin(TwoWire* wirePort) {
  if (wirePort != nullptr) {
    wire_ = wirePort;
  } else if (wire_ == nullptr) {
    wire_ = &Wire1;
  }

  ready_ = false;
  status_ = IMUStatus::DISCONNECTED;
  lastRetryMs_ = millis();

  // 1. Dò tìm địa chỉ I2C của MPU6050: 0x68 (AD0=GND), 0x69 (AD0=VCC hoặc để hở)
  const uint8_t candidateAddresses[] = { I2C_ADDR_MPU6050, 0x69 };
  uint8_t foundAddr = 0;

  for (uint8_t addr : candidateAddresses) {
    wire_->beginTransmission(addr);
    if (wire_->endTransmission() == 0) {
      foundAddr = addr;
      break;
    }
  }

  if (foundAddr == 0) {
    status_ = IMUStatus::DISCONNECTED;
    return Availability::UNAVAILABLE;
  }

  i2cAddr_ = foundAddr;

  // 2. Reset chip phần cứng để xóa mọi trạng thái treo/lỗi trước đó (bit 7: DEVICE_RESET)
  writeRegister(REG_PWR_MGMT_1, 0x80);
  delay(50);

  // 3. Đánh thức chip và chọn nguồn xung nhịp PLL với trục X gyro (0x01)
  // CLKSEL=1 ổn định hơn rất nhiều so với dao động nội RC 8MHz (0x00)
  if (!writeRegister(REG_PWR_MGMT_1, 0x01)) {
    status_ = IMUStatus::ERROR;
    return Availability::ERROR;
  }
  delay(15);

  // 4. Đọc kiểm tra mã nhận diện WHO_AM_I (0x75)
  uint8_t id = 0;
  if (readRegisters(REG_WHO_AM_I, &id, 1)) {
    whoAmI_ = id;
    // Chấp nhận các chip tương thích họ InvenSense:
    // 0x68: MPU-6050, 0x70: MPU-6500, 0x71/0x73: MPU-9250, 0x72, 0x98...
    Serial.printf("[MPU6050] Phát hiện thiết bị tại 0x%02X (WHO_AM_I = 0x%02X)\n", i2cAddr_, whoAmI_);
  } else {
    Serial.printf("[MPU6050] CẢNH BÁO: Không đọc được WHO_AM_I tại 0x%02X\n", i2cAddr_);
  }

  // 5. Cấu hình tốc độ chia mẫu: Sample Rate = Gyro Rate / (1 + SMPLRT_DIV) -> 1 kHz
  writeRegister(REG_SMPLRT_DIV, 0x00);

  // 6. Cấu hình Digital Low Pass Filter (DLPF): mode 3 (~44 Hz bandwidth)
  writeRegister(REG_CONFIG, 0x03);

  // 7. Cấu hình thang đo Gyro: 0 = ±250 °/s (131 LSB/(°/s))
  writeRegister(REG_GYRO_CONFIG, 0x00);

  // 8. Cấu hình thang đo Accel: 0 = ±2 g (16384 LSB/g)
  writeRegister(REG_ACCEL_CONFIG, 0x00);

  ready_ = true;
  status_ = IMUStatus::VALID;
  consecutiveErrors_ = 0;
  resetFilters();
  Serial.printf("[MPU6050] OK — Khởi tạo thành công tại 0x%02X (±2 g / ±250 °/s, Bộ lọc EMA ON)\n", i2cAddr_);
  return Availability::READY;
}

void MPU6050Sensor::resetFilters() {
  axFilter_.reset();
  ayFilter_.reset();
  azFilter_.reset();
  gxFilter_.reset();
  gyFilter_.reset();
  gzFilter_.reset();
}

MPU6050Data MPU6050Sensor::read() {
  MPU6050Data data{};
  data.whoAmI = whoAmI_;

  // Nếu cảm biến chưa sẵn sàng, thử kết nối lại không nghẽn định kỳ (mỗi 3 giây)
  if (!ready_) {
    const unsigned long now = millis();
    if (now - lastRetryMs_ >= I2C_RETRY_INTERVAL_MS) {
      lastRetryMs_ = now;
      if (begin() == Availability::READY) {
        Serial.println(F("[MPU6050] >>> Phục hồi kết nối thành công! <<<"));
      }
    }
    data.status = status_;
    return data;
  }

  uint8_t buffer[14];
  if (!readRegisters(REG_ACCEL_XOUT_H, buffer, 14)) {
    consecutiveErrors_++;
    // Nếu lỗi liên tiếp quá 5 lần, chuyển sang trạng thái ngắt kết nối để tự động reconnect
    if (consecutiveErrors_ >= 5) {
      ready_ = false;
      status_ = IMUStatus::DISCONNECTED;
      resetFilters();
      Serial.println(F("[MPU6050] CẢNH BÁO: Mất kết nối I2C liên tiếp > 5 lần, chuyển sang chế độ phục hồi tự động."));
    }
    data.status = status_;
    return data;
  }

  consecutiveErrors_ = 0;
  status_ = IMUStatus::VALID;

  int16_t rawAx = static_cast<int16_t>((buffer[0] << 8) | buffer[1]);
  int16_t rawAy = static_cast<int16_t>((buffer[2] << 8) | buffer[3]);
  int16_t rawAz = static_cast<int16_t>((buffer[4] << 8) | buffer[5]);

  int16_t rawTemp = static_cast<int16_t>((buffer[6] << 8) | buffer[7]);

  int16_t rawGx = static_cast<int16_t>((buffer[8] << 8) | buffer[9]);
  int16_t rawGy = static_cast<int16_t>((buffer[10] << 8) | buffer[11]);
  int16_t rawGz = static_cast<int16_t>((buffer[12] << 8) | buffer[13]);

  // Bù trừ lật úp cảm biến: đảo chiều trục Y và Z (xoay 180° quanh trục X)
  const float valAx =  (static_cast<float>(rawAx) / 16384.0f) * 9.80665f;
  const float valAy = -(static_cast<float>(rawAy) / 16384.0f) * 9.80665f;
  const float valAz = -(static_cast<float>(rawAz) / 16384.0f) * 9.80665f;

  data.rawAx = valAx;
  data.rawAy = valAy;
  data.rawAz = valAz;

  // Lọc EMA cho 3 trục gia tốc (m/s²): triệt tiêu rung giật cơ học
  data.ax = axFilter_.update(valAx);
  data.ay = ayFilter_.update(valAy);
  data.az = azFilter_.update(valAz);

  data.accelMagnitude = sqrtf(data.ax * data.ax + data.ay * data.ay + data.az * data.az);

  data.temperature = (static_cast<float>(rawTemp) / 340.0f) + 36.53f;

  // Bù trừ lật úp: đảo chiều Gy và Gz
  const float valGxDeg =  static_cast<float>(rawGx) / 131.0f;
  const float valGyDeg = -static_cast<float>(rawGy) / 131.0f;
  const float valGzDeg = -static_cast<float>(rawGz) / 131.0f;

  constexpr float kDegToRad = 3.14159265358979323846f / 180.0f;
  data.rawGx_deg = valGxDeg;
  data.rawGy_deg = valGyDeg;
  data.rawGz_deg = valGzDeg;
  data.rawGx     = valGxDeg * kDegToRad;
  data.rawGy     = valGyDeg * kDegToRad;
  data.rawGz     = valGzDeg * kDegToRad;

  // Lọc EMA cho 3 trục vận tốc góc (°/s): khử nhiễu trắng con quay
  data.gx_deg = gxFilter_.update(valGxDeg);
  data.gy_deg = gyFilter_.update(valGyDeg);
  data.gz_deg = gzFilter_.update(valGzDeg);

  data.gx = data.gx_deg * kDegToRad;
  data.gy = data.gy_deg * kDegToRad;
  data.gz = data.gz_deg * kDegToRad;

  data.status = IMUStatus::VALID;
  data.valid = true;
  return data;
}

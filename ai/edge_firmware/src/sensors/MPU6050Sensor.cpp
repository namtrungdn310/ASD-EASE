#include "MPU6050Sensor.h"
#include <esp_timer.h>
#include <Wire.h>
#include <algorithm>
#include <cmath>

namespace {
constexpr uint32_t kPeriodMs = 1000 / IMU_SAMPLE_RATE_HZ;
constexpr float kAccelLsb[] = {16384, 8192, 4096, 2048};
constexpr float kGyroLsb[] = {131, 65.5, 32.8, 16.4};
static_assert(IMU_SAMPLE_RATE_HZ == 50 && IMU_FILTER_BW == 5,
              "Revalidate filtering, FIFO clock and acquisition profile for a new rate");
static_assert(IMU_ACCEL_RANGE == 0 && IMU_GYRO_RANGE == 0,
              "Movement score/clipping limits require the validated 2g/250dps profile");
}

bool MPU6050Sensor::writeRegister(uint8_t reg, uint8_t value) {
  wire_->beginTransmission(i2cAddr_);
  wire_->write(reg); wire_->write(value);
  return wire_->endTransmission() == 0;
}

bool MPU6050Sensor::readRegisters(uint8_t reg, uint8_t* buffer, size_t len) {
  wire_->beginTransmission(i2cAddr_); wire_->write(reg);
  if (wire_->endTransmission(false) != 0) return false;
  if (wire_->requestFrom(i2cAddr_, static_cast<uint8_t>(len)) != len) {
    while (wire_->available()) (void)wire_->read();
    return false;
  }
  for (size_t i = 0; i < len; ++i) {
    if (!wire_->available()) return false;
    buffer[i] = static_cast<uint8_t>(wire_->read());
  }
  return true;
}

void MPU6050Sensor::fail() {
  ready_ = false; initStage_ = 0; status_ = IMUStatus::ERROR;
  lastRetryMs_ = millis();
  latest_ = {}; clock_.reset();
  resetFilters();
  if (!gyroBias_.ready()) gyroBias_.restartWindow();
}

Availability MPU6050Sensor::begin(TwoWire* port) {
  wire_ = port ? port : (wire_ ? wire_ : &Wire1);
  ready_ = false; initStage_ = 0; lastRetryMs_ = millis();
  whoAmI_ = 0; latest_ = {}; clock_.reset();
  gyroBias_.reset(); resetFilters();
  bool found = false;
  for (uint8_t address : {I2C_ADDR_MPU6050, uint8_t(0x69)}) {
    i2cAddr_ = address;
    uint8_t id = 0;
    if (!readRegisters(0x75, &id, 1)) continue;
    whoAmI_ = id;
    // Không coi MPU6500/9250 hoặc mã lạ là 6050: FIFO/filter/nhiệt độ có thể khác.
    if (id != 0x68 && id != 0x74) {
      Serial.printf("[IMU] WHO_AM_I=0x%02X tại 0x%02X chưa có profile; không gửi số giả hợp lệ\n", id, address);
      continue;
    }
    found = true; break;
  }
  if (!found) { status_ = IMUStatus::DISCONNECTED; return Availability::UNAVAILABLE; }
  if (!writeRegister(0x6b, 0x80)) { fail(); return Availability::ERROR; }
  // Chờ reset/wake bằng state machine, không delay(50/15) trong sensing.
  initStage_ = 1; stageStarted_ = millis(); status_ = IMUStatus::CALIBRATING;
  return Availability::UNAVAILABLE;
}

bool MPU6050Sensor::resetFifo() {
  return writeRegister(0x23, 0x00) && writeRegister(0x6a, 0x00) &&
      writeRegister(0x6a, 0x04) && writeRegister(0x6a, 0x40) && writeRegister(0x23, 0xf8);
}

bool MPU6050Sensor::configure() {
  const uint8_t divider = 1000 / IMU_SAMPLE_RATE_HZ - 1;
  const uint8_t gyro = IMU_GYRO_RANGE << 3, accel = IMU_ACCEL_RANGE << 3;
  // MPU6515 (0x74): nhánh MPU6500 có ACCEL_CONFIG2 riêng; bit6 chọn FIFO1KiB.
  const bool is6515 = whoAmI_ == 0x74;
  if (!writeRegister(0x19, divider) || !writeRegister(0x1a, IMU_FILTER_BW) ||
      !writeRegister(0x1b, gyro) || !writeRegister(0x1c, accel) ||
      (is6515 && !writeRegister(0x1d, 0x40 | IMU_FILTER_BW)) ||
      !writeRegister(0x37, 0x00) || !writeRegister(0x38, 0x10) || !resetFifo()) return false;
  uint8_t registers[4]{}, fifo = 0, user = 0, power = 0, id = 0;
  if (!readRegisters(0x19, registers, 4) || registers[0] != divider ||
      registers[1] != IMU_FILTER_BW || registers[2] != gyro || registers[3] != accel ||
      !readRegisters(0x23, &fifo, 1) || fifo != 0xf8 ||
      !readRegisters(0x6a, &user, 1) || (user & 0x40) == 0 ||
      !readRegisters(0x6b, &power, 1) || (power & 0x47) != 0x01 ||
      !readRegisters(0x75, &id, 1) || id != whoAmI_) return false;
  if (is6515) {
    uint8_t accelFilter = 0;
    if (!readRegisters(0x1d, &accelFilter, 1) || (accelFilter & 0x7f) != (0x40 | IMU_FILTER_BW)) return false;
  }
  Serial.printf("[IMU] ID=0x%02X %s FIFO50Hz DLPF~10Hz ±2g/250dps; gyro-bias=%u, giữ yên khi khởi động\n",
      whoAmI_, is6515 ? "MPU6515" : "MPU6050", unsigned(IMU_AUTO_GYRO_BIAS));
  return true;
}

void MPU6050Sensor::resetFilters() {
  movement_.reset();
  axFilter_.reset(); ayFilter_.reset(); azFilter_.reset();
  gxFilter_.reset(); gyFilter_.reset(); gzFilter_.reset();
}

MPU6050Data MPU6050Sensor::process(const asd::ImuRawSample& raw, uint64_t measured) {
  MPU6050Data data{};
  data.whoAmI = whoAmI_; data.sampleMonotonicMs = measured;
  data.sampleUpdatedAtMs = static_cast<uint32_t>(measured); data.hasSampleTimestamp = true;
  const auto clip = [](int16_t axis) { return axis <= -32760 || axis >= 32760; };
  accelerationQuality_.add(measured, clip(raw.ax) || clip(raw.ay) || clip(raw.az));
  rotationQuality_.add(measured, clip(raw.gx) || clip(raw.gy) || clip(raw.gz));
  if (clip(raw.ax) || clip(raw.ay) || clip(raw.az) || clip(raw.gx) || clip(raw.gy) || clip(raw.gz)) {
    ++stats_.clipped; resetFilters();
    if (!gyroBias_.ready()) gyroBias_.restartWindow();
    data.status = IMUStatus::ERROR; return data;
  }
  // Hệ trục đã thống nhất: lật Y/Z một lần, giữ raw trước EMA và trước bù offset.
  const float scale = 9.80665f / kAccelLsb[IMU_ACCEL_RANGE];
  data.rawAx = raw.ax * scale; data.rawAy = -raw.ay * scale; data.rawAz = -raw.az * scale;
  data.rawGx_deg = raw.gx / kGyroLsb[IMU_GYRO_RANGE];
  data.rawGy_deg = -raw.gy / kGyroLsb[IMU_GYRO_RANGE];
  data.rawGz_deg = -raw.gz / kGyroLsb[IMU_GYRO_RANGE];
  constexpr float radians = 3.14159265358979323846f / 180;
  data.rawGx = data.rawGx_deg * radians; data.rawGy = data.rawGy_deg * radians;
  data.rawGz = data.rawGz_deg * radians;
  // Không áp hệ số nhiệt của6050 cho6515 khi chưa xác minh riêng; không gửi lên MQTT.
  data.temperature = whoAmI_ == 0x68 ? raw.temperature / 340.0f + 36.53f : NAN;
  const bool hadBias = gyroBias_.ready();
  data.gyroCalibrated = IMU_AUTO_GYRO_BIAS && gyroBias_.update(measured,
      {{data.rawAx, data.rawAy, data.rawAz}}, {{data.rawGx_deg, data.rawGy_deg, data.rawGz_deg}});
  if (IMU_AUTO_GYRO_BIAS && !data.gyroCalibrated) {
    data.status = IMUStatus::CALIBRATING; return data;
  }
  if (!hadBias && data.gyroCalibrated) resetFilters();
  const auto bias = gyroBias_.offsets();
  data.ax = axFilter_.update(data.rawAx); data.ay = ayFilter_.update(data.rawAy);
  data.az = azFilter_.update(data.rawAz);
  data.gx_deg = gxFilter_.update(data.rawGx_deg - bias[0]);
  data.gy_deg = gyFilter_.update(data.rawGy_deg - bias[1]);
  data.gz_deg = gzFilter_.update(data.rawGz_deg - bias[2]);
  data.gx = data.gx_deg * radians; data.gy = data.gy_deg * radians; data.gz = data.gz_deg * radians;
  data.accelMagnitude = std::sqrt(data.ax*data.ax + data.ay*data.ay + data.az*data.az);
  // Score v1 giữ đúng định nghĩa trước EMA/bù offset; UI dùng hai vector có đơn vị.
  const auto movement = movement_.update(measured, data.rawAx, data.rawAy, data.rawAz,
      data.rawGx_deg, data.rawGy_deg, data.rawGz_deg);
  data.movementScore = movement.score; data.movementValid = movement.valid;
  data.status = IMUStatus::VALID; data.valid = true;
  return data;
}

MPU6050Data MPU6050Sensor::read() {
  const uint32_t now = millis();
  if (!ready_) {
    if (initStage_ == 1 && uint32_t(now - stageStarted_) >= 100) {
      if (!writeRegister(0x6b, 0x01)) fail();
      else { initStage_ = 2; stageStarted_ = now; }
    } else if (initStage_ == 2 && uint32_t(now - stageStarted_) >= 30) {
      if (!configure()) fail();
      else { ready_ = true; initStage_ = 0; lastFifoMs_ = now; }
    } else if (initStage_ == 0 && uint32_t(now - lastRetryMs_) >= I2C_RETRY_INTERVAL_MS) {
      (void)begin();
    }
    MPU6050Data data{}; data.status = status_; data.whoAmI = whoAmI_; return data;
  }
  struct Transport {
    MPU6050Sensor* sensor;
    bool read(uint8_t reg, uint8_t* bytes, size_t size) { return sensor->readRegisters(reg, bytes, size); }
  } transport{this};
  asd::ImuRawSample samples[8];
  const auto batch = asd::readImuFifo(transport, samples);
  if (batch.status != asd::ImuFifoStatus::Ok) {
    ++stats_.gaps;
    if (batch.status == asd::ImuFifoStatus::IoError) ++stats_.ioErrors;
    if (batch.status == asd::ImuFifoStatus::Overflow) ++stats_.overflowEvents;
    fail();
    MPU6050Data data{}; data.status = status_; return data;
  }
  if (batch.count == 0) {
    if (uint32_t(now - lastFifoMs_) > 500) {
      ++stats_.gaps; fail(); MPU6050Data data{}; data.status = status_; return data;
    }
    auto data = latest_; data.newSamples = 0; return data;
  }
  lastFifoMs_ = now;
  const uint64_t captured = static_cast<uint64_t>(esp_timer_get_time()) / 1000;
  const uint64_t span = (batch.count - 1) * kPeriodMs;
  if (captured < span) { ++stats_.gaps; fail(); return {}; }
  const auto timing = clock_.batch(captured, static_cast<uint32_t>(batch.count), kPeriodMs);
  if (timing.gap) {
    ++stats_.gaps; resetFilters();
    if (!gyroBias_.ready()) gyroBias_.restartWindow();
  }
  for (size_t i = 0; i < batch.count; ++i) {
    latest_ = process(samples[i], timing.first + i * kPeriodMs);
    if(observer_)observer_(latest_);
  }
  stats_.samples += static_cast<uint32_t>(batch.count);
  latest_.newSamples = static_cast<uint32_t>(batch.count);
  status_ = latest_.status;
  return latest_;
}

#pragma once
#include <cstddef>
#include <cstdint>

namespace asd {
struct ImuRawSample { int16_t ax, ay, az, temperature, gx, gy, gz; };
enum class ImuFifoStatus { Ok, IoError, Overflow, Backlog };
struct ImuFifoResult {
  ImuFifoStatus status = ImuFifoStatus::Ok;
  size_t count = 0;
  uint16_t pending = 0;
};

// MPU6050 FIFO_EN=0xf8: accel, temperature, gyro XYZ, 14 byte/mẫu.
template <typename Transport>
ImuFifoResult readImuFifo(Transport& transport, ImuRawSample (&samples)[8]) {
  ImuFifoResult result;
  uint8_t interrupt = 0, bytes[2]{};
  if (!transport.read(0x3a, &interrupt, 1) || !transport.read(0x72, bytes, 2)) {
    result.status = ImuFifoStatus::IoError; return result;
  }
  const uint16_t size = (uint16_t(bytes[0]) << 8) | bytes[1];
  result.pending = size / 14;
  if ((interrupt & 0x10) != 0 || size >= 1024) {
    result.status = ImuFifoStatus::Overflow; return result;
  }
  if (result.pending > 8) {
    result.status = ImuFifoStatus::Backlog; return result;
  }
  // Byte dư có thể do FIFO đang ghi một mẫu; để nguyên cho lượt tiếp theo.
  for (size_t i = 0; i < result.pending; ++i) {
    uint8_t frame[14]{};
    if (!transport.read(0x74, frame, sizeof(frame))) {
      result.status = ImuFifoStatus::IoError; return result;
    }
    int16_t words[7]{};
    for (size_t j = 0; j < 7; ++j) {
      const uint16_t value = (uint16_t(frame[2*j]) << 8) | frame[2*j+1];
      words[j] = static_cast<int16_t>(value >= 32768 ? int32_t(value) - 65536 : value);
    }
    samples[i] = {words[0], words[1], words[2], words[3], words[4], words[5], words[6]};
  }
  if (result.pending != 0) {
    if (!transport.read(0x3a, &interrupt, 1)) result.status = ImuFifoStatus::IoError;
    else if ((interrupt & 0x10) != 0) result.status = ImuFifoStatus::Overflow;
    if (result.status != ImuFifoStatus::Ok) return result;
  }
  result.count = result.pending;
  return result;
}
}  // namespace asd

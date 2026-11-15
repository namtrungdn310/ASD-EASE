#pragma once

#include <cstddef>
#include <cstdint>

namespace asd {

struct PpgSample {
  uint32_t red = 0;
  uint32_t ir = 0;
};

enum class PpgFifoStatus { Ok, IoError, Overflow, AmbiguousFull, PowerReset };

struct PpgFifoResult {
  PpgFifoStatus status = PpgFifoStatus::Ok;
  size_t count = 0;
  uint8_t overflowLowerBound = 0;  // Bộ đếm phần cứng bão hòa ở 31.
  bool almostFull = false;
  bool ambientOverflow = false;
  uint8_t writePointer = 0, readPointer = 0, interrupt = 0;
};

// Bỏ dữ liệu không còn liên tục bằng pop FIFO: thao tác này xóa OVF_COUNTER
// trên chip. Không reset/retry3s mãi trước khi pop, khiến bộ đếm lỗi bị giữ lại.
template <typename Transport>
bool discardPpgFifo(Transport& transport, const PpgFifoResult& fault, uint32_t& discarded) {
  const size_t pending = (fault.writePointer + 32 - fault.readPointer) % 32;
  const size_t count = pending == 0 ? 32 : pending;
  discarded = 0;
  for (size_t offset = 0; offset < count;) {
    const size_t n = count - offset < 5 ? count - offset : 5;
    uint8_t bytes[30]{};
    if (!transport.read(0x07, bytes, n * 6)) return false;
    discarded += static_cast<uint32_t>(n);
    offset += n;
  }
  return true;
}

// Chỉ dùng SpO2 mode hai kênh RED/IR. Kiểm tra overflow trước khi pop,
// kể cả khi rollover được bật để tương thích module đang dùng.
// Transport.read(reg, bytes, length) phải trả false nếu thiếu bất kỳ byte nào.
// Đọc thẳng FIFO phần cứng để không đi qua ring 4 phần tử của SparkFun.
template <typename Transport>
PpgFifoResult readPpgFifo(Transport& transport, PpgSample (&samples)[32]) {
  PpgFifoResult result;
  uint8_t interrupts = 0;
  uint8_t pointers[3]{};  // WR_PTR, OVF_COUNTER, RD_PTR.
  // Đọc riêng metadata để tương thích module không tăng địa chỉ khi burst 0x04.
  // Dữ liệu FIFO 0x07 vẫn phải đọc burst đầy đủ RED/IR.
  if (!transport.read(0x00, &interrupts, 1) ||
      !transport.read(0x04, &pointers[0], 1) ||
      !transport.read(0x05, &pointers[1], 1) ||
      !transport.read(0x06, &pointers[2], 1)) {
    result.status = PpgFifoStatus::IoError;
    return result;
  }
  result.almostFull = (interrupts & 0x80) != 0;
  result.writePointer = pointers[0] & 0x1f;
  result.readPointer = pointers[2] & 0x1f;
  result.interrupt = interrupts;
  result.ambientOverflow = (interrupts & 0x20) != 0;
  result.overflowLowerBound = pointers[1] & 0x1f;
  if ((interrupts & 0x01) != 0) {
    result.status = PpgFifoStatus::PowerReset;
    return result;
  }
  // Kiểm tra trước khi đọc FIFO: pop một mẫu sẽ xóa OVF_COUNTER.
  if (result.overflowLowerBound != 0) {
    result.status = PpgFifoStatus::Overflow;
    return result;
  }
  const size_t pending = ((pointers[0] & 0x1f) + 32 - (pointers[2] & 0x1f)) % 32;
  if (pending == 0 && result.almostFull) {
    // WR=RD có thể là đầy 32 mẫu, không được coi là rỗng rồi nối RR qua khoảng mất.
    result.status = PpgFifoStatus::AmbiguousFull;
    return result;
  }

  // Chụp số mẫu đầu lượt; không lặp vô hạn nếu cảm biến tiếp tục sinh mẫu.
  // 5 mẫu/lần = 30 byte, phù hợp cả Wire buffer 32 byte.
  for (size_t offset = 0; offset < pending;) {
    const size_t count = pending - offset < 5 ? pending - offset : 5;
    uint8_t bytes[30]{};
    if (!transport.read(0x07, bytes, count * 6)) {
      // Có thể đã pop nửa mẫu: hủy cả lô, caller khởi tạo lại trước lượt sau.
      result.status = PpgFifoStatus::IoError;
      result.count = 0;
      return result;
    }
    for (size_t i = 0; i < count; ++i) {
      const size_t at = i * 6;
      samples[offset + i].red = ((uint32_t(bytes[at]) << 16) |
          (uint32_t(bytes[at + 1]) << 8) | bytes[at + 2]) & 0x3ffff;
      samples[offset + i].ir = ((uint32_t(bytes[at + 3]) << 16) |
          (uint32_t(bytes[at + 4]) << 8) | bytes[at + 5]) & 0x3ffff;
    }
    offset += count;
  }
  // Kiểm tra A_FULL sau burst để phát hiện sát/tràn bộ đệm trong lúc I2C chậm.
  // Thà hủy lô không chắc chắn còn hơn nối một khoảng RR sai.
  if (pending != 0) {
    uint8_t after = 0;
    if (!transport.read(0x00, &after, 1)) {
      result.status = PpgFifoStatus::IoError;
      return result;
    }
    result.ambientOverflow = result.ambientOverflow || (after & 0x20) != 0;
    if ((after & 0x01) != 0) {
      result.status = PpgFifoStatus::PowerReset;
      return result;
    }
    if ((after & 0x80) != 0) {
      result.status = PpgFifoStatus::AmbiguousFull;
      return result;
    }
  }
  result.count = pending;
  return result;
}

}  // namespace asd

#pragma once
#include <cstdint>

namespace asd {

// Cổng tiếp xúc kỹ thuật, không phải phép đo chất lượng hay xác nhận nhịp sinh lý.
// Giữ cửa sổ PPG qua sụt sáng rất ngắn và thay đổi DC do dịch chuyển nhẹ;
// chỉ reset khi tín hiệu thật sự mất liên tục quá debounce.
class PpgContact {
 public:
  struct State { bool present = false, settled = false, usable = false, restart = false; };
  PpgContact(uint32_t on, uint32_t off, uint32_t settleMs)
      : on_(on), off_(off), settleMs_(settleMs) {}
  void reset() { present_ = settled_ = hasTime_ = low_ = false; }
  State update(uint32_t ir, uint64_t now) {
    bool restart = false;
    if (hasTime_ && (now <= lastTime_ || now - lastTime_ > 100)) { reset(); restart = true; }
    lastTime_ = now; hasTime_ = true;
    if (!present_) {
      if (ir >= on_) {
        present_ = true; low_ = false; since_ = now; restart = true;
      }
    } else if (ir < off_) {
      if (!low_) { low_ = true; lowSince_ = now; }
      if (now - lowSince_ >= kLossDebounceMs) {
        present_ = settled_ = low_ = false;
        restart = true;
      }
    } else {
      // Một lần tụt dưới ngưỡng dưới kLossDebounceMs không làm mất cửa sổ.
      // Lọc thông dải và bộ kiểm tra chu kỳ sẽ loại xung chuyển tiếp; không
      // bắt người dùng chờ lại 8 giây chỉ vì cổ tay xê dịch nhẹ.
      if (low_) low_ = false;
    }
    if (present_ && !low_ && now - since_ >= settleMs_) settled_ = true;
    return {present_, settled_ && !low_, present_ && settled_, restart};
  }
  bool present() const { return present_; }
  bool settled() const { return settled_ && !low_; }
 private:
  static constexpr uint64_t kLossDebounceMs = 100;
  uint32_t on_, off_, settleMs_;
  uint64_t since_ = 0, lowSince_ = 0, lastTime_ = 0;
  bool present_ = false, settled_ = false, hasTime_ = false, low_ = false;
};
}  // namespace asd

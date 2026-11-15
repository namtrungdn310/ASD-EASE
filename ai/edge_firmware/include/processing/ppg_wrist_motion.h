#pragma once
#include <cmath>
#include <cstdint>

namespace asd {
// Cổng phát triển bảo thủ cho HR khi nghỉ, không phải thuật toán bù chuyển động.
// Score motion-rms-v1 không có đơn vị. Ngưỡng này chưa hiệu chuẩn trên người.
class WristMotionGuard {
 public:
  enum class Reason : uint8_t { UnknownImu, Moving, CleaningWindow, Still };
  bool update(uint64_t now,uint64_t measured,bool valid,bool calibrated,bool scoreValid,float score) {
    const bool known=valid && calibrated && scoreValid && std::isfinite(score) && score>=0 && score<=1 &&
                     measured<=now && now-measured<=100;
    // Hysteresis: loại chuyển động rõ nhưng không khóa HR vì rung nhỏ quanh
    // một ngưỡng duy nhất. Các giá trị là cổng kỹ thuật phát triển, chưa hiệu chuẩn.
    const bool quiet=known && (wasQuiet_ ? score<.30f : score<.22f);
    const bool resetWindow=quiet!=wasQuiet_ || (!hasTime_ || now<lastTime_ || now-lastTime_>100);
    if (resetWindow) { since_=now; wasQuiet_=quiet; }
    lastTime_=now; hasTime_=true;
    if (!known) reason_=Reason::UnknownImu;
    else if (!quiet) reason_=Reason::Moving;
    else reason_=now-since_>=2000 ? Reason::Still : Reason::CleaningWindow;
    return resetWindow;
  }
  bool allowsHr() const { return reason_==Reason::Still; }
  Reason reason() const { return reason_; }
 private:
  uint64_t since_=0,lastTime_=0;
  bool wasQuiet_=false,hasTime_=false;
  Reason reason_=Reason::UnknownImu;
};
} // namespace asd

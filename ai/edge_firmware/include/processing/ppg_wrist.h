#pragma once
#include <cmath>
#include <cstdint>

namespace asd {
// Chẩn đoán quang cho cổ tay. Không thay ngưỡng công nhận HR hoặc schema MQTT.
enum class WristOpticalLevel : uint8_t { NoReturn, Settling, Overload, Warming, Weak, Unresolved, Measuring };
struct WristOptics {
  WristOpticalLevel level=WristOpticalLevel::NoReturn;
  float acDcPct=0; // Biên độ RMS tương đương/DC; không phải PI đã hiệu chuẩn.
};
inline WristOptics assessWrist(uint32_t ir,float amplitude,bool hasWindow,
                              bool contact,bool settled,bool overload,bool hrValid) {
  WristOptics r{};
  if (ir && std::isfinite(amplitude) && amplitude>=0) r.acDcPct=amplitude*100/ir;
  if (overload) r.level=WristOpticalLevel::Overload;
  else if (!contact) r.level=WristOpticalLevel::NoReturn;
  else if (!settled) r.level=WristOpticalLevel::Settling;
  else if (hrValid) r.level=WristOpticalLevel::Measuring;
  else if (!hasWindow) r.level=WristOpticalLevel::Warming;
  else if (r.acDcPct<.02f) r.level=WristOpticalLevel::Weak;
  else r.level=WristOpticalLevel::Unresolved;
  return r;
}
inline const char* wristLevelName(WristOpticalLevel level) {
  switch(level) {
    case WristOpticalLevel::NoReturn:return "THIEU_PHAN_XA";
    case WristOpticalLevel::Settling:return "DANG_ON_DINH";
    case WristOpticalLevel::Overload:return "QUA_SANG";
    case WristOpticalLevel::Warming:return "DANG_THU_CUA_SO";
    case WristOpticalLevel::Weak:return "DAO_DONG_YEU";
    case WristOpticalLevel::Unresolved:return "CHUA_TACH_DUOC_NHIP";
    case WristOpticalLevel::Measuring:return "CO_HR_HOP_LE";
  }
  return "KHONG_RO";
}
} // namespace asd

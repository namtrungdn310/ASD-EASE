#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>

namespace asd {
// Độ lặp hình dạng theo chu kỳ ứng viên, không phải xác suất HR đúng.
// Mỗi chu kỳ được chuẩn hóa riêng để không ưu tiên xung có biên độ lớn.
// Workspace thuộc task phân tích; không đặt mảng lớn trên stack hoặc cấp heap.
class PpgCycleShape {
 public:
  float evaluate(const float* signal,size_t length,float bpm) {
    if (!signal || (length!=200 && length!=400) || !std::isfinite(bpm) || bpm<30 || bpm>210) return 0;
    const float period=3000/bpm;
    const size_t cycles=std::min(size_t(26),size_t(float(length-1)/period));
    if (cycles<2) return 0;
    waves_={};sums_.fill(0);qualities_.fill(0);
    // Neo về cuối cửa sổ đã thu, không để phần mới nhất bị bỏ qua vì lẻ chu kỳ.
    const float start=float(length-1)-cycles*period;
    for(size_t cycle=0;cycle<cycles;++cycle) {
      float mean=0,norm=0;
      for(size_t j=0;j<16;++j) {
        const float at=start+cycle*period+period*j/16;
        const size_t lo=size_t(at);
        const float fraction=at-lo;
        const float low=signal[lo],high=signal[std::min(length-1,lo+1)];
        if (!std::isfinite(low) || !std::isfinite(high)) return 0;
        waves_[cycle][j]=low+fraction*(high-low);
        mean+=waves_[cycle][j]/16;
      }
      for(float& value:waves_[cycle]) {value-=mean;norm+=value*value;}
      if(norm<1e-8f) continue;
      norm=std::sqrt(norm);
      for(size_t j=0;j<16;++j) {waves_[cycle][j]/=norm;sums_[j]+=waves_[cycle][j];}
    }
    for(size_t cycle=0;cycle<cycles;++cycle) {
      float dot=0,norm=0;
      for(size_t j=0;j<16;++j) {
        // Chu kỳ đang chấm không góp vào template của chính nó.
        const float other=sums_[j]-waves_[cycle][j];
        dot+=other*waves_[cycle][j];norm+=other*other;
      }
      qualities_[cycle]=norm>1e-8f ? std::max(0.f,dot/std::sqrt(norm)) : 0;
    }
    std::sort(qualities_.begin(),qualities_.begin()+cycles);
    return .5f*(qualities_[cycles/2]+qualities_[(cycles-1)/2]);
  }
 private:
  std::array<std::array<float,16>,26> waves_{};
  std::array<float,16> sums_{};
  std::array<float,26> qualities_{};
};
} // namespace asd

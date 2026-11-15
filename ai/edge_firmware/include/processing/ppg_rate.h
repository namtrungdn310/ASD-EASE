#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include "processing/sensor_math.h"
#include "processing/ppg_filter.h"
#include "processing/ppg_motion.h"

namespace asd {

// Ước tính HR theo cửa sổ, không phải phát hiện từng nhịp hoặc số liệu HRV.
// Ngưỡng dưới đây là cổng kỹ thuật phát triển, chưa được kiểm định lâm sàng.
class PpgRate {
 public:
  static constexpr size_t kSamples = 400;  // 8 giây ở FIFO50Hz.
  struct Estimate {
    bool updated = false, valid = false;
    float bpm = 0, periodicity = 0, amplitude = 0;
    float candidateBpm = 0, recentBpm = 0, redBpm = 0, recentPeriodicity = 0, redPeriodicity = 0;
    float redRecentPeriodicity = 0, bandPowerRatio = 0;
    uint8_t source = 0;  // 0: chưa có HR, 1: IR, 2: RED; không phải quality0..1.
    uint64_t measuredAt = 0;
  };
  void reset() {
    head_ = count_ = sinceEvaluation_ = warmup_ = 0;
    initialized_ = hasTime_ = false;
    hasCandidate_ = false;
    ir_ = {}; red_ = {}; result_ = {};
    motionFilters_={};motionWarmup_=0;motionValid_.fill(false);
  }
  Estimate update(uint32_t ir, uint32_t red, uint64_t measured,const PpgMotionSample* motion=nullptr) {
    result_.updated = false;
    if (hasTime_ && (measured <= last_ || measured - last_ > 40)) reset();
    last_ = measured; hasTime_ = true;
    if (!initialized_) {
      irDc_ = float(ir); redDc_ = float(red); initialized_ = true;
    }
    // Tách DC trước bộ lọc; khởi tạo theo mẫu đầu để tránh xung giả lúc bật.
    const float a = ir_.apply(float(ir) - irDc_);
    const float b = red_.apply(float(red) - redDc_);
    std::array<float,6> filteredMotion{};
    const bool aligned=motion && motion->valid && (motion->at>measured?motion->at-measured:measured-motion->at)<=25;
    if(aligned) {
      ++motionWarmup_;
      for(size_t a=0;a<6;++a)filteredMotion[a]=motionFilters_[a].apply(motion->axes[a]);
    } else {motionFilters_={};motionWarmup_=0;}
    if (warmup_ < 100) { ++warmup_; return result_; }  // Bỏ2 giây quá độ bộ lọc.
    irValues_[head_] = {a,ir_.noisePower}; redValues_[head_] = {b,red_.noisePower};
    motionValid_[head_]=aligned && motionWarmup_>=100;
    for(size_t a=0;a<6;++a)motionValues_[a][head_]=filteredMotion[a];
    head_ = (head_ + 1) % kSamples;
    if (count_ < kSamples) ++count_;
    if (count_ < kSamples || ++sinceEvaluation_ < 50) return result_;
    sinceEvaluation_ = 0;
    result_ = {}; result_.updated = true; result_.measuredAt = measured;
    const auto full = period(irValues_, kSamples);
    const auto recent = period(irValues_, kSamples / 2);
    const auto redPeriod = period(redValues_, kSamples);
    const auto redRecent = period(redValues_, kSamples / 2);
    result_.periodicity = full.correlation;
    result_.amplitude = full.amplitude;
    result_.candidateBpm = full.bpm; result_.recentBpm = recent.bpm; result_.redBpm = redPeriod.bpm;
    result_.recentPeriodicity = recent.correlation; result_.redPeriodicity = redPeriod.correlation;
    result_.redRecentPeriodicity = redRecent.correlation;
    const auto agrees = [](const Period& a, const Period& b) {
      return a.valid && b.valid && std::fabs(a.bpm-b.bpm) <= .12f*a.bpm;
    };
    const bool irGood = agrees(full,recent), redGood = agrees(redPeriod,redRecent);
    // Mỗi kênh phải độc lập qua cả8s/4s; hai kênh rõ nhưng bất đồng thì từ chối.
    if ((!irGood && !redGood) || (irGood && redGood && !agrees(full,redPeriod))) {
      hasCandidate_ = false; return result_;
    }
    const bool chooseRed = redGood && (!irGood ||
        std::min(redPeriod.correlation,redRecent.correlation) > std::min(full.correlation,recent.correlation));
    const auto& chosen = chooseRed ? redPeriod : full;
    // Cần hai lần kiểm tra liên tiếp thống nhất; không cho một cửa sổ nhiễu
    // lẻ làm Dashboard hiện HR. Các cửa sổ chồng nhau, không gọi là độc lập.
    const bool confirmed = hasCandidate_ && measured > candidateAt_ && measured-candidateAt_ <= 1500 &&
                           std::fabs(chosen.bpm-candidateBpm_) <= .12f*chosen.bpm;
    hasCandidate_ = true; candidateBpm_ = chosen.bpm; candidateAt_ = measured;
    if (!confirmed) return result_;
    result_.valid = true;
    result_.bpm = chosen.bpm; result_.source = chooseRed ? 2 : 1;
    result_.amplitude = chosen.amplitude; result_.bandPowerRatio = chosen.bandPowerRatio;
    return result_;
  }
  const Estimate& estimate() const { return result_; }
  // Chụp cửa sổ đã lọc để task quality xử lý riêng; không thay phép tính baseline.
  bool copyFilteredWindow(std::array<float,kSamples>& ir,std::array<float,kSamples>& red) const {
    if (count_!=kSamples) return false;
    for (size_t i=0;i<kSamples;++i) {
      ir[i]=irValues_[(head_+i)%kSamples].filtered;
      red[i]=redValues_[(head_+i)%kSamples].filtered;
    }
    return true;
  }

  void copyMotionWindow(PpgMotionWindow& out) const {
    for(size_t i=0;i<kSamples;++i){
      const size_t at=(head_+i)%kSamples;out.valid[i]=count_==kSamples && motionValid_[at];
      for(size_t a=0;a<6;++a)out.axes[a][i]=motionValues_[a][at];
    }
  }
 private:
  using Filter = PpgBandpass;
  struct Point { float filtered = 0, noisePower = 0; };
  struct Period { bool valid = false; float bpm = 0, correlation = 0, amplitude = 0, bandPowerRatio = 0; };
  const Point& point(const std::array<Point,kSamples>& data, size_t length, size_t i) const {
    return data[(head_ + kSamples - length + i) % kSamples];
  }
  Period period(const std::array<Point,kSamples>& data, size_t length) {
    Period p;
    // Trừ đường xu hướng tuyến tính trong từng cửa sổ trước đối chiếu chu kỳ.
    float mean = 0, slope = 0, xx = 0, noisePower = 0;
    const float center = float(length - 1) * .5f;
    for (size_t i = 0; i < length; ++i) {
      const float x = float(i) - center;
      const auto& s = point(data,length,i);
      mean += s.filtered; slope += x*s.filtered; xx += x*x; noisePower += s.noisePower;
    }
    mean /= length; slope /= xx;
    float energy = 0, tailEnergy = 0;
    for (size_t i = 0; i < length; ++i) {
      const float v = point(data,length,i).filtered - mean - slope*(float(i)-center);
      scratch_[i] = v; energy += v*v;
      if (i >= length - 75) tailEnergy += v*v;
    }
    p.amplitude = 2 * std::sqrt(2*energy/length);
    // Sàn4 counts gần lượng tử ADC; thay50 counts bằng đối chiếu công suất/nhiễu.
    // Hệ số0,2 là xấp xỉ bảo thủ cho băng lọc/25Hz Nyquist, không phải SNR đo chuẩn.
    p.bandPowerRatio = (energy/length) / std::max(.25f,noisePower/length*.2f);
    const float minimumCorrelation=.60f;
    const bool signalUsable = p.amplitude >= 4 && p.bandPowerRatio >= 2.f &&
                             tailEnergy/75 >= energy/length*.12f;
    if (energy <= .0001f) return p;
    std::array<float,77> correlations{};
    for (size_t lag = 14; lag <= 76; ++lag) {
      float sumA = 0, sumB = 0, aa = 0, bb = 0, ab = 0;
      const float n = float(length - lag);
      for (size_t i = lag; i < length; ++i) {
        const float a = scratch_[i], b = scratch_[i-lag];
        sumA += a; sumB += b; aa += a*a; bb += b*b; ab += a*b;
      }
      const float denominator = (aa - sumA*sumA/n) * (bb - sumB*sumB/n);
      correlations[lag] = denominator > 0 ? (ab - sumA*sumB/n)/std::sqrt(denominator) : 0;
    }
    float best = 0;
    for (size_t lag = 15; lag <= 75; ++lag)
      if (correlations[lag] >= correlations[lag-1] && correlations[lag] > correlations[lag+1])
        best = std::max(best,correlations[lag]);
    p.correlation = best;
    if (best < minimumCorrelation || !signalUsable) return p;
    for (size_t lag = 15; lag <= 75; ++lag) {
      const float left = correlations[lag-1], mid = correlations[lag], right = correlations[lag+1];
      // Chọn chu kỳ ngắn nhất qua cùng ngưỡng chất lượng0,60. Không yêu cầu
      // nó gần đỉnh tương quan toàn cục: xung lớn/nhỏ xen kẽ làm đỉnh2RR cao hơn
      // và luật90% cũ có thể khóa về nửa nhịp dù đỉnh1RR đã đủ rõ.
      if (mid < minimumCorrelation || mid < left || mid <= right) continue;
      const float denominator = left - 2*mid + right;
      const float offset = lag > 15 && lag < 75 && denominator < -.000001f
                               ? .5f*(left-right)/denominator : 0;
      const float bpm = 3000 / (float(lag) + std::max(-.5f,std::min(.5f,offset)));
      if (bpm < 40 || bpm > 200) continue;
      p.valid = true; p.bpm = bpm; p.correlation = mid; break;
    }
    return p;
  }
  std::array<Point,kSamples> irValues_{}, redValues_{};
  // Workspace cố định để tránh chia modulo trong vòng tương quan và cấp phát heap.
  std::array<float,kSamples> scratch_{};
  Filter ir_{}, red_{};
  std::array<Filter,6> motionFilters_{};
  std::array<std::array<float,kSamples>,6> motionValues_{};
  std::array<bool,kSamples> motionValid_{};
  uint32_t motionWarmup_=0;
  Estimate result_{};
  size_t head_ = 0, count_ = 0, sinceEvaluation_ = 0;
  uint32_t warmup_ = 0;
  uint64_t last_ = 0;
  uint64_t candidateAt_ = 0;
  float candidateBpm_ = 0;
  float irDc_ = 0, redDc_ = 0;
  bool initialized_ = false, hasTime_ = false, hasCandidate_ = false;
};
}  // namespace asd

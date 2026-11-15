// Sóng có nhãn qua đúng bộ lọc/tracker; không dùng nhịp của người làm số đích.
#include "processing/ppg_rate.h"
#include "processing/ppg_cycle_tracker.h"
#include <cstdlib>
#include <iostream>

namespace {
constexpr double pi=3.14159265358979323846;
void check(bool ok,const char* message) {
  if (!ok) { std::cerr<<"FAIL: "<<message<<'\n';std::exit(1); }
}
struct Noise {
  uint32_t state=57191;
  float next() {
    state=1664525u*state+1013904223u;
    return (float(state>>8)/16777216.f-.5f)*3.464101615f;
  }
};
struct Stream {
  asd::PpgRate filter;
  asd::PpgCycleTracker tracker;
  Noise noise;
  double phase=0;
  asd::PpgCycleTracker::Result step(unsigned index,float bpm,float amplitude,float noiseLevel,float harmonic) {
    phase+=2*pi*bpm/3000;
    const double pulse=amplitude*(std::sin(phase)+harmonic*std::sin(2*phase+.3));
    const auto at=uint64_t(1000+index*20);
    const auto estimate=filter.update(uint32_t(170000+pulse+noiseLevel*noise.next()),
                                     uint32_t(100000+.7*pulse+noiseLevel*noise.next()),at);
    if (!estimate.updated) return {};
    asd::PpgCycleTracker::Window ir{},red{};
    if (!filter.copyFilteredWindow(ir,red)) return {};
    return tracker.update(ir,red,at,1);
  }
};
}

int main() {
  unsigned cases=0;
  for (unsigned bpm=40;bpm<=200;bpm+=10) {
    Stream stream;unsigned accepted=0;
    for (unsigned i=0;i<30*50;++i) {
      const auto result=stream.step(i,float(bpm),100,2,.25f);
      if (!result.valid) continue;
      check(std::fabs(result.bpm-bpm)<3,"steady range: wrong or half/double rate");
      ++accepted;
    }
    check(accepted>=17,"steady range: rejected too many valid windows");++cases;
  }
  for (unsigned profile=0;profile<3;++profile) {
    Stream stream;double error=0;unsigned accepted=0;unsigned bucketCount[5]{};
    double bucketError[5]{};
    for (unsigned i=0;i<600*50;++i) {
      const float t=float(i)/50;
      const float target=t<300 ? 40+.5f*t : 190-.5f*(t-300);
      const auto result=stream.step(i,target,profile==1 ? 20.f : 100.f,
                                    profile==1 ? 12.f : 2.f,profile==2 ? 1.3f : .25f);
      if (!result.valid) continue;
      const double e=std::fabs(result.bpm-target);
      check(e<10,"ramp: wrong track or excessive lag");
      error+=e;++accepted;
      const unsigned bucket=target<60 ? 0 : target<90 ? 1 : target<120 ? 2 : target<160 ? 3 : 4;
      ++bucketCount[bucket];bucketError[bucket]+=e;
    }
    check(accepted>=560,"ramp: reduced error only by withholding results");
    // Mục tiêu độ trễ trung bình <=7s tương đương3,5bpm ở tốc độ0,5bpm/s.
    // Đây là yêu cầu mô phỏng, không phải sai số đo cổ tay trên người.
    check(error/accepted<3.5,"ramp: average tracking lag exceeds seven seconds");
    for(unsigned b=0;b<5;++b) {
      check(bucketCount[b]>=50,"ramp: missing an HR range");
      check(bucketError[b]/bucketCount[b]<3.6,"ramp: lag biased towards one HR range");
    }
    std::cout<<"Ramp profile="<<profile<<" accepted="<<accepted<<" MAE="<<error/accepted<<" bpm\n";
    ++cases;
  }
  std::cout<<"PASS: "<<cases<<" full-range cases (synthetic, not wrist accuracy)\n";
}

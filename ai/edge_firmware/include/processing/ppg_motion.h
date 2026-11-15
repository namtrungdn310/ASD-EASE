#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace asd {
struct PpgMotionSample {uint64_t at=0;std::array<float,6> axes{};bool valid=false;};
struct PpgMotionWindow {
  std::array<std::array<float,400>,6> axes{};
  std::array<bool,400> valid{};
};
// Chỉ sensing task ghi/đọc; worker nhận bản copy. Không ghép mẫu khác boot/gap.
class PpgMotionHistory {
 public:
  void add(const PpgMotionSample& s) {
    if(count_ && s.at<=last_) {count_=next_=0;}
    last_=s.at; samples_[next_]=s;next_=(next_+1)%samples_.size();
    count_=std::min(count_+1,samples_.size());
  }
  PpgMotionSample nearest(uint64_t at) const {
    PpgMotionSample best{};uint64_t gap=26;
    for(size_t i=0;i<count_;++i) {
      const auto& s=samples_[i];const auto d=s.at>at?s.at-at:at-s.at;
      if(s.valid && d<gap) {best=s;gap=d;}
    }
    return best;
  }
 private:
  std::array<PpgMotionSample,32> samples_{};size_t count_=0,next_=0;uint64_t last_=0;
};

// NLMS sáu trục, ba tap/trục. Fit trên 6s, kiểm giảm nhiễu trên 2s cuối
// trước khi dùng. Không suy HR từ IMU và không phát nhịp nếu pulse trùng cadence.
class PpgMotionCleaner {
 public:
  using Window=std::array<float,400>;
  float coverage=0,residualIr=1,residualRed=1;
  bool active=false,irApplied=false,redApplied=false;
  Window ir{},red{};
  void prepare(const Window& inputIr,const Window& inputRed,const PpgMotionWindow* motion) {
    coverage=0;active=irApplied=redApplied=false;residualIr=residualRed=1;
    ir=inputIr;red=inputRed;enabled_.fill(false);
    if(!motion)return;
    unsigned validCount=0;for(bool valid:motion->valid)validCount+=valid;
    coverage=float(validCount)/400;
    if(coverage<.95f)return;
    for(size_t a=0;a<6;++a) {
      float mean=0;unsigned count=0;
      for(size_t i=0;i<400;++i)if(motion->valid[i]){mean+=motion->axes[a][i];++count;}
      mean/=std::max(1u,count);float energy=0;
      for(size_t i=0;i<400;++i) {
        refs_[a][i]=motion->valid[i]?motion->axes[a][i]-mean:0;
        energy+=refs_[a][i]*refs_[a][i];
      }
      const float rms=std::sqrt(energy/400);
      if(rms<.005f || !std::isfinite(rms))continue;
      enabled_[a]=active=true;
      for(float& v:refs_[a])v=std::max(-6.f,std::min(6.f,v/rms));
    }
    if(!active)return;
    irApplied=clean(inputIr,ir,residualIr);redApplied=clean(inputRed,red,residualRed);
  }
  float overlap(float bpm)const {
    if(!active || coverage<.95f || !std::isfinite(bpm))return 0;
    float strongest=0;
    for(size_t a=0;a<6;++a)if(enabled_[a]) {
      float energy=0;for(float v:refs_[a])energy+=v*v;
      for(float delta:{-.1f,0.f,.1f}) {
        float s=0,c=0;
        for(size_t i=0;i<400;++i) {
          const float angle=6.28318530718f*(bpm/60+delta)*float(i)/50;
          s+=refs_[a][i]*std::sin(angle);c+=refs_[a][i]*std::cos(angle);
        }
        strongest=std::max(strongest,2*(s*s+c*c)/std::max(1e-9f,400*energy));
      }
    }
    return std::min(1.f,strongest);
  }
 private:
  bool clean(const Window& input,Window& output,float& ratio) {
    std::array<float,18> weights{};
    float mean=0;for(float v:input)mean+=v/400;
    for(unsigned epoch=0;epoch<3;++epoch)for(size_t i=2;i<300;++i) {
      float predicted=0,norm=.001f;
      for(size_t a=0;a<6;++a)if(enabled_[a])for(size_t lag=0;lag<3;++lag) {
        const float x=refs_[a][i-lag];predicted+=weights[3*a+lag]*x;norm+=x*x;
      }
      const float error=input[i]-mean-predicted;
      for(size_t a=0;a<6;++a)if(enabled_[a])for(size_t lag=0;lag<3;++lag)
        weights[3*a+lag]+=.06f*error*refs_[a][i-lag]/norm;
    }
    float before=0,after=0;
    for(size_t i=0;i<400;++i) {
      float predicted=0;
      for(size_t a=0;a<6;++a)if(enabled_[a])for(size_t lag=0;lag<3;++lag)
        if(i>=lag)predicted+=weights[3*a+lag]*refs_[a][i-lag];
      output[i]=input[i]-predicted;
      if(i>=300){before+=(input[i]-mean)*(input[i]-mean);after+=(output[i]-mean)*(output[i]-mean);}
    }
    ratio=after/std::max(1e-9f,before);
    if(!std::isfinite(ratio) || ratio<.08f || ratio>.90f){output=input;return false;}
    return true;
  }
  std::array<Window,6> refs_{};std::array<bool,6> enabled_{};
};
}

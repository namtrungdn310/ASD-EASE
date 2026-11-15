#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include "processing/ppg_cycle_shape.h"
#include "processing/ppg_motion.h"

namespace asd {
// Bộ theo dõi chu kỳ thử nghiệm. Bằng chứng phổ/tự tương quan không phải
// xác suất HR đúng. Workspace cố định, chỉ gọi ở task phân tích riêng.
class PpgCycleTracker {
 public:
  static constexpr size_t kBins=181;
  static constexpr int kFirstBpm=30;
  using Window=std::array<float,400>;
  struct Result {
    bool qualified=false,valid=false;
    float bpm=0,rawBpm=0,massScore=0,evidence=0,amplitude=0;
    uint64_t measuredAt=0;
    uint32_t generation=0;
    uint8_t source=5;
    float sqi=0,irEvidence=0,redEvidence=0,motionCoverage=0,motionOverlap=0;
    bool motionSupported=false,motionCorrected=false;
  };
  PpgCycleTracker() {
    for (size_t i=0;i<400;++i) hannFull_[i]=.5f-.5f*std::cos(2*pi*i/399);
    for (size_t i=0;i<200;++i) hannRecent_[i]=.5f-.5f*std::cos(2*pi*i/199);
    for (int d=-12;d<=12;++d) transition_[d+12]=std::exp(-float(d*d)/18.f);
    reset();
  }
  void reset() {
    posterior_.fill(1.f/kBins); consecutive_=weak_=0; hasTime_=false;
    smoothCount_=smoothHead_=0;smoothed_=0;lastAccepted_=0;
    trendCount_=0;
    anchorBpm_=jumpBpm_=0;jumpCount_=0;anchorAt_=0;
    pendingBpm_=0;
  }
  Result update(const Window& ir,const Window& red,uint64_t at,uint32_t generation,const PpgMotionWindow* motion=nullptr) {
    if (hasTime_ && (generation!=generation_ || at<=last_ || at-last_>1500)) reset();
    hasTime_=true;last_=at;generation_=generation;
    Result r{}; r.measuredAt=at;r.generation=generation;
    float a=0,b=0;
    bool useIr=channel(ir,channelScores_[0],a,channelQuality_[0]);
    bool useRed=channel(red,channelScores_[1],b,channelQuality_[1]);
    cleaner_.prepare(ir,red,motion);
    r.motionCoverage=cleaner_.coverage;
    bool correctedIr=false,correctedRed=false;
    for(size_t c=0;c<2;++c) {
      const bool applied=c==0?cleaner_.irApplied:cleaner_.redApplied;
      if(!applied)continue;
      float amplitude=0;
      const bool usable=channel(c==0?cleaner_.ir:cleaner_.red,candidateScores_,amplitude,candidateQuality_);
      const bool removesCadence=cleaner_.overlap(peakRate(channelScores_[c]))>=.45f &&
          cleaner_.overlap(peakRate(candidateScores_))<.35f &&
          strength(candidateScores_)>=.15f && prominence(candidateScores_)>=.04f;
      if(usable && (strength(candidateScores_)>strength(channelScores_[c])+.025f || removesCadence)) {
        channelScores_[c]=candidateScores_;channelQuality_[c]=candidateQuality_;
        if(c==0){useIr=true;a=amplitude;}else{useRed=true;b=amplitude;}
        if(c==0)correctedIr=true;else correctedRed=true;
      }
    }
    r.irEvidence=strength(channelScores_[0]);r.redEvidence=strength(channelScores_[1]);
    // Kênh yếu không được kéo kênh tốt xuống bằng trung bình ngang nhau.
    useIr=useIr && r.irEvidence>=.12f && prominence(channelScores_[0])>=.035f;
    useRed=useRed && r.redEvidence>=.12f && prominence(channelScores_[1])>=.035f;
    r.amplitude=std::max(a,b);
    if (!useIr && !useRed) {
      // Cửa sổ yếu không phải một lần tiếp xúc/boot mới: vẫn giữ lịch sử
      // có giới hạn để không mất cổng xác nhận nửa/gấp đôi nhịp sau một lần lỗi.
      // Không phát HR cũ, không tăng confirmation từ dữ liệu thiếu bằng chứng.
      consecutive_=0;jumpCount_=0;
      if (++weak_>=15) reset();
      return r;
    }
    if (useIr && useRed) {
      const auto ia=std::max_element(channelScores_[0].begin(),channelScores_[0].end());
      const auto ib=std::max_element(channelScores_[1].begin(),channelScores_[1].end());
      const float ba=float(kFirstBpm+std::distance(channelScores_[0].begin(),ia));
      const float bb=float(kFirstBpm+std::distance(channelScores_[1].begin(),ib));
      if (*ia>=.65f && *ib>=.65f && std::fabs(ba-bb)>.12f*ba) {reset();return r;}
    }
    r.motionCorrected=(useIr && correctedIr)||(useRed && correctedRed);
    r.source=useIr && useRed ? 5 : useIr ? 6 : 7;
    const float irWeight=useIr?std::pow(prominence(channelScores_[0]),2):0;
    const float redWeight=useRed?std::pow(prominence(channelScores_[1]),2):0;
    const float weight=std::max(1e-9f,irWeight+redWeight);
    float best=0,mean=0;
    for (size_t k=0;k<kBins;++k) {
      const float x=channelScores_[0][k],y=channelScores_[1][k];
      observations_[k]=(irWeight*x+redWeight*y)/weight;
      best=std::max(best,observations_[k]);mean+=observations_[k]/kBins;
    }
    // Prior đều trên30..210 để nhận ra dao động ngoài dải xuất40..200.
    // Luôn chừa2% cho giả thuyết mới,
    // tránh khóa vĩnh viễn quanh một số sai hoặc một nửa/gấp đôi nhịp.
    float total=0;
    for (int k=0;k<int(kBins);++k) {
      float prior=0,weight=0;
      for (int d=-12;d<=12;++d) if (k+d>=0 && k+d<int(kBins)) {
        const float w=transition_[d+12];
        prior+=posterior_[k+d]*w;weight+=w;
      }
      next_[k]=(.02f/kBins+.98f*prior/weight)*std::exp(12.f*(observations_[k]-best));
      total+=next_[k];
    }
    if (!(total>0) || !std::isfinite(total)) { reset();return r; }
    size_t peak=0;
    for (size_t k=0;k<kBins;++k) {
      posterior_[k]=next_[k]/total;
      if (posterior_[k]>posterior_[peak]) peak=k;
    }
    float mass=0;
    for (int k=std::max(0,int(peak)-8);k<=std::min(int(kBins)-1,int(peak)+8);++k) {
      mass+=posterior_[k];
    }
    r.massScore=std::max(0.f,std::min(1.f,(mass-17.f/kBins)/(1-17.f/kBins)));
    r.evidence=observations_[peak];
    const int peakBpm=int(peak)+kFirstBpm;
    r.motionOverlap=cleaner_.overlap(float(peakBpm));
    const float irPeak=peakRate(channelScores_[0]),redPeak=peakRate(channelScores_[1]);
    const float disagreement=std::fabs(irPeak-redPeak)/std::max(5.f,.1f*peakBpm);
    const float agreement=useIr && useRed ? 1/std::sqrt(1+disagreement*disagreement) : .85f;
    const float motionFactor=1-.5f*r.motionOverlap;
    r.sqi=std::max(0.f,std::min(1.f,(irWeight*channelQuality_[0][peak]+redWeight*channelQuality_[1][peak])/weight*agreement*motionFactor));

    const auto strongest=std::max_element(observations_.begin(),observations_.end());
    const float observedBpm=float(kFirstBpm+std::distance(observations_.begin(),strongest));
    const bool startupConflict=!anchorAt_ && *strongest-r.evidence>.10f &&
        std::fabs(observedBpm-peakBpm)>std::max(8.f,.15f*peakBpm);
    // Giả thuyết ngoài dải vẫn được theo dõi để không kẹp một trôi nền
    // 30..39bpm thành HR40. Chỉ xuất ước tính trong40..200bpm.
    r.qualified=!startupConflict && peakBpm>=40 && peakBpm<=200 && best>=.15f && best-mean>=.04f && observations_[peak]>=.12f && mass>=.22f;
    if(cleaner_.active && r.motionOverlap>=.45f)r.qualified=false;
    r.motionSupported=r.motionCoverage>=.95f && r.qualified &&
        (!cleaner_.active || r.motionOverlap<.45f);
    if (!r.qualified) {
      consecutive_=0;
      jumpCount_=0;
      if (++weak_>=15) reset();
      return r; // Giữ giả thuyết ngắn hạn, không phát HR mới chỉ từ prior.
    }
    weak_=0; ++consecutive_;
    float offset=0;
    if (peakBpm>40 && peakBpm<200) {
      const float a=posterior_[peak-1],b=posterior_[peak],c=posterior_[peak+1],denom=a-2*b+c;
      if (denom< -1e-12f) offset=std::max(-.5f,std::min(.5f,.5f*(a-c)/denom));
    }
    r.rawBpm=float(peakBpm)+offset;
    // Hai cửa sổ đủ chất lượng chưa chắc cùng một chu kỳ: lúc chưa có
    // anchor, không xác nhận82→40 chỉ vì cả hai đều vượt cổng quality.
    if (!anchorAt_ && pendingBpm_>0 &&
        std::fabs(r.rawBpm-pendingBpm_)>std::max(8.f,.15f*pendingBpm_)) consecutive_=1;
    pendingBpm_=r.rawBpm;
    r.valid=consecutive_>=2;
    bool confirmedTrackChange=false;
    if (r.valid && anchorAt_ && at-anchorAt_<=15000 &&
        std::fabs(r.rawBpm-anchorBpm_)>std::max(12.f,.18f*anchorBpm_)) {
      // Không lập tức đổi một quỹ đạo đang theo dõi sang nửa/gấp đôi nhịp.
      // Nhịp40 thật vẫn được nhận khi bằng chứng mới tồn tại đủ lâu.
      const float ratio=r.rawBpm/anchorBpm_;
      const bool harmonic=(ratio>=.45f && ratio<=.60f) || (ratio>=1.8f && ratio<=2.2f);
      if (jumpCount_ && std::fabs(r.rawBpm-jumpBpm_)<=.08f*jumpBpm_) ++jumpCount_;
      else jumpCount_=1;
      jumpBpm_=r.rawBpm;
      if (jumpCount_<(harmonic ? 6u : 3u)) {r.valid=false;return r;}
      confirmedTrackChange=true;
    }
    if (r.valid) {
      anchorBpm_=r.rawBpm;anchorAt_=at;jumpCount_=0;
      // Làm mượt chỉ trên kết quả có bằng chứng mới. Không update từ read()
      // cache, không tạo số trong cửa sổ yếu hoặc sau mất tiếp xúc/reset.
      // Chu kỳ mới đã qua đủ xác nhận: không trộn median/EMA của chu kỳ cũ
      // (ví dụ đã nhận80 nhưng vẫn xuất40). Thay đổi nhỏ vẫn làm mượt bình thường.
      if (confirmedTrackChange || !smoothCount_ || at-lastAccepted_>15000) {
        smoothCount_=smoothHead_=0;trendCount_=0;
      }
      smoothValues_[smoothHead_]=r.rawBpm;smoothHead_=(smoothHead_+1)%3;
      smoothCount_=std::min(size_t(3),smoothCount_+1);
      auto sorted=smoothValues_;std::sort(sorted.begin(),sorted.begin()+smoothCount_);
      const float median=smoothCount_%2 ? sorted[smoothCount_/2] : .5f*(sorted[0]+sorted[1]);
      // Chỉ bám nhanh hơn khi5 ứng viên mới liên tiếp tạo xu hướng đều.
      // Không ngoại suy, không đổi chọn chu kỳ, không phát HR từ cửa sổ bị loại.
      if (at-lastAccepted_>1500) trendCount_=0;
      for(size_t i=0;i<4;++i) trendValues_[i]=trendValues_[i+1];
      trendValues_[4]=r.rawBpm;trendCount_=std::min(size_t(5),trendCount_+1);
      bool coherentTrend=trendCount_==5;
      const float slope=(trendValues_[4]-trendValues_[0])/4;
      coherentTrend=coherentTrend && std::fabs(slope)>=.3f && std::fabs(slope)<=1.5f;
      for(size_t i=1;i<5;++i) {
        const float delta=trendValues_[i]-trendValues_[i-1];
        coherentTrend=coherentTrend && delta*slope>0 && std::fabs(delta-slope)<.35f;
      }
      const float alpha=coherentTrend ? .50f : .30f;
      smoothed_=smoothCount_==1 ? median : smoothed_+alpha*(median-smoothed_);
      lastAccepted_=at;r.bpm=smoothed_;
    }
    return r;
  }

 private:
  static constexpr float pi=3.14159265358979323846f;
  static void detrend(float* x,size_t n) {
    float mean=0,slope=0,xx=0,c=float(n-1)*.5f;
    for (size_t i=0;i<n;++i) { const float t=float(i)-c;mean+=x[i];slope+=t*x[i];xx+=t*t; }
    mean/=n;slope/=xx;
    for (size_t i=0;i<n;++i) x[i]-=mean+slope*(float(i)-c);
  }
  static float median(std::array<float,400>& sorted) {
    std::sort(sorted.begin(),sorted.end());return .5f*(sorted[199]+sorted[200]);
  }
  void fftPower(const float* x,size_t n,std::array<float,257>& power) {
    real_.fill(0);imag_.fill(0);
    for (size_t i=0;i<n;++i) real_[i]=x[i]*(n==400 ? hannFull_[i] : hannRecent_[i]);
    for (size_t i=1,j=0;i<512;++i) {
      size_t bit=256;
      for (;j&bit;bit>>=1) j^=bit;
      j^=bit;
      if (i<j) std::swap(real_[i],real_[j]);
    }
    for (size_t length=2;length<=512;length<<=1) {
      const float angle=-2*pi/length,wr=std::cos(angle),wi=std::sin(angle);
      for (size_t start=0;start<512;start+=length) {
        float ar=1,ai=0;
        for (size_t j=0;j<length/2;++j) {
          const size_t a=start+j,b=a+length/2;
          const float br=real_[b]*ar-imag_[b]*ai,bi=real_[b]*ai+imag_[b]*ar;
          real_[b]=real_[a]-br;imag_[b]=imag_[a]-bi;
          real_[a]+=br;imag_[a]+=bi;
          const float next=ar*wr-ai*wi;ai=ar*wi+ai*wr;ar=next;
        }
      }
    }
    float total=0;
    for (size_t k=0;k<=256;++k) {
      power[k]=real_[k]*real_[k]+imag_[k]*imag_[k];
      if (k*50.f/512>=.5f && k*50.f/512<=4.f) total+=power[k];
    }
    for (float& p:power) p=total>1e-12f ? p/total : 0;
  }
  static float band(const std::array<float,257>& power,float frequency) {
    if (frequency<.5f || frequency>4.f) return 0;
    float total=0;
    constexpr float binWidth=50.f/512;
    for (size_t k=6;k<=40;++k) {
      const float center=k*binWidth;
      // Tính cả phần bin giao nhau: tránh bước nhảy giả khi lưới HR1bpm
      // đi qua mép bin FFT rộng khoảng5,86bpm.
      const float overlap=std::max(0.f,std::min(center+.5f*binWidth,frequency+.15f)-
                                      std::max(center-.5f*binWidth,frequency-.15f));
      total+=power[k]*overlap/binWidth;
    }
    return total;
  }
  static void correlations(const float* x,size_t n,std::array<float,103>& out) {
    out.fill(0);
    for (size_t lag=14;lag<=101;++lag) {
      float a=0,b=0,aa=0,bb=0,ab=0;const float count=float(n-lag);
      for (size_t i=lag;i<n;++i) {
        const float u=x[i],v=x[i-lag];a+=u;b+=v;aa+=u*u;bb+=v*v;ab+=u*v;
      }
      const float denominator=(aa-a*a/count)*(bb-b*b/count);
      out[lag]=denominator>1e-12f ? std::max(0.f,(ab-a*b/count)/std::sqrt(denominator)) : 0;
    }
  }
  static float atLag(const std::array<float,103>& correlation,float bpm) {
    const float lag=3000/bpm;const size_t left=static_cast<size_t>(lag);
    return correlation[left]+(correlation[std::min(size_t(102),left+1)]-correlation[left])*(lag-left);
  }
  static float strength(const std::array<float,kBins>& scores){return *std::max_element(scores.begin(),scores.end());}
  static float prominence(const std::array<float,kBins>& scores){
    float mean=0;for(float s:scores)mean+=s/kBins;return std::max(0.f,strength(scores)-mean);
  }
  static float peakRate(const std::array<float,kBins>& scores){
    return float(kFirstBpm+std::distance(scores.begin(),std::max_element(scores.begin(),scores.end())));
  }
  bool channel(const Window& input,std::array<float,kBins>& scores,float& amplitude,std::array<float,kBins>& quality) {
    scores.fill(0);quality.fill(0);
    for (size_t i=0;i<400;++i) {
      if (!std::isfinite(input[i])) return false;
      values_[i]=input[i];
    }
    detrend(values_.data(),400);
    sorted_=values_;const float center=median(sorted_);
    for (size_t i=0;i<400;++i) sorted_[i]=std::fabs(values_[i]-center);
    const float scale=1.4826f*median(sorted_);
    if (scale<1e-6f) return false;
    for (float& x:values_) x=std::max(center-6*scale,std::min(center+6*scale,x));
    detrend(values_.data(),400);
    float energy=0,tail=0;
    for (size_t i=0;i<400;++i) { energy+=values_[i]*values_[i];if(i>=325)tail+=values_[i]*values_[i]; }
    amplitude=2*std::sqrt(2*energy/400);
    if (amplitude<4 || tail/75<energy/400*.12f) return false;
    correlations(values_.data(),400,fullCorrelation_);
    std::copy(values_.begin()+200,values_.end(),recent_.begin());detrend(recent_.data(),200);
    correlations(recent_.data(),200,recentCorrelation_);
    fftPower(values_.data(),400,fullPower_);fftPower(recent_.data(),200,recentPower_);
    for (size_t k=0;k<kBins;++k) {
      const float bpm=float(k+kFirstBpm),frequency=bpm/60;
      const float full=band(fullPower_,frequency),recent=band(recentPower_,frequency);
      const float fullSpectrum=std::min(1.f,full+.20f*std::sqrt(full*band(fullPower_,2*frequency)));
      const float recentSpectrum=std::min(1.f,recent+.20f*std::sqrt(recent*band(recentPower_,2*frequency)));
      // Chỉ giảm điểm khi các chu kỳ không lặp hình dạng; không cộng bằng chứng
      // cho nhiễu hoặc ép HR về một khoảng nhịp nghỉ của người dùng.
      const float fullShape=cycleShape_.evaluate(values_.data(),400,bpm);
      const float recentShape=cycleShape_.evaluate(recent_.data(),200,bpm);
      const float fullScore=(.55f*fullSpectrum+.45f*atLag(fullCorrelation_,bpm))*(.25f+.75f*fullShape);
      const float recentScore=(.55f*recentSpectrum+.45f*atLag(recentCorrelation_,bpm))*(.25f+.75f*recentShape);
      scores[k]=.4f*fullScore+.6f*recentScore;
      // SQI kỹ thuật: trung bình nhân bốn bằng chứng chuẩn hóa0..1.
      // Không dùng posterior, HR làm mượt hoặc đổi thang để nâng điểm.
      const float periodicity=std::sqrt(std::max(0.f,atLag(fullCorrelation_,bpm)*atLag(recentCorrelation_,bpm)));
      const float purity=std::sqrt(std::max(0.f,fullSpectrum*recentSpectrum));
      const float shape=std::sqrt(std::max(0.f,fullShape*recentShape));
      const float consistency=std::min(fullScore,recentScore)/std::max(.001f,std::max(fullScore,recentScore));
      quality[k]=std::pow(std::max(0.f,periodicity*purity*shape*consistency),.25f);
    }
    return true;
  }
  PpgCycleShape cycleShape_;
  PpgMotionCleaner cleaner_;
  std::array<std::array<float,kBins>,2> channelQuality_{};
  std::array<float,kBins> candidateScores_{},candidateQuality_{};
  std::array<float,kBins> posterior_{},next_{},observations_{};
  std::array<std::array<float,kBins>,2> channelScores_{};
  std::array<float,400> values_{},sorted_{};
  std::array<float,200> recent_{};
  std::array<float,512> real_{},imag_{};
  std::array<float,257> fullPower_{},recentPower_{};
  std::array<float,103> fullCorrelation_{},recentCorrelation_{};
  std::array<float,400> hannFull_{};
  std::array<float,200> hannRecent_{};
  std::array<float,25> transition_{};
  std::array<float,3> smoothValues_{};
  std::array<float,5> trendValues_{};
  size_t trendCount_=0;
  size_t smoothCount_=0,smoothHead_=0;
  float smoothed_=0;uint64_t lastAccepted_=0;
  float anchorBpm_=0,jumpBpm_=0,pendingBpm_=0;uint64_t anchorAt_=0;unsigned jumpCount_=0;
  uint64_t last_=0;uint32_t generation_=0;
  unsigned consecutive_=0,weak_=0;bool hasTime_=false;
};
} // namespace asd

#pragma once
// C++ port of the selected offline hybrid_strict candidate. MSPTD core adapted
// from Peter H. Charlton's ppg-beats c397be7afc0d8a1601a85cd673718372e40f1f59.
// Copyright (c) 2022, 2024 Peter H. Charlton. MIT License:
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace asd {
// Workspace cố định, không cấp phát heap. Chỉ gọi từ task phân tích riêng.
class PpgQuality {
 public:
  using Window = std::array<float,400>;
  enum class Reason : uint8_t { Computed, InvalidWindow, LowAmplitude, InsufficientBeats,
                              RrRange, RecentDisagreement, StalePeak, FlatBeat };
  struct Feature {
    bool usable = false;
    Reason reason = Reason::InvalidWindow;
    double bpm = 0, recentBpm = 0, amplitude = 0, rrCv = 0;
    double templateMedian = 0, templateP20 = 0, spectralFraction = 0, peakAge = 0;
    uint16_t peaks = 0;
    bool qualifies() const {
      return usable && rrCv <= .12 && templateMedian >= .90 &&
             templateP20 >= .75 && spectralFraction >= .65;
    }
  };
  struct Result {
    Feature ir{}, red{};
    uint64_t measuredAt = 0;
    uint32_t generation = 0;
    double bpm = 0;
    uint8_t source = 0;  // 3: IR quality, 4: RED quality; chỉ chẩn đoán.
    bool qualified = false, valid = false;
    float sqi=0,irEvidence=0,redEvidence=0,motionCoverage=0,motionOverlap=0;
    bool motionSupported=false,motionCorrected=false;
    float trackingMassScore = 0, trackingEvidence = 0, trackingRawBpm = 0; // Chỉ tracker; không phải xác suất đúng.
  };
  PpgQuality() {
    for (size_t i=0;i<400;++i) hann_[i]=.5-.5*std::cos(2*pi()*double(i)/399);
    for (size_t k=4;k<=32;++k) coefficients_[k-4]=2*std::cos(2*pi()*double(k)/400);
  }
  void reset() { hasCandidate_=false; }
  Result update(const Window& ir,const Window& red,uint64_t measuredAt,uint32_t generation) {
    Result r{}; r.measuredAt=measuredAt; r.generation=generation;
    r.ir=analyze(ir); r.red=analyze(red);
    const bool a=r.ir.qualifies(), b=r.red.qualifies();
    if (a && b && std::fabs(r.ir.bpm-r.red.bpm)>.12*r.ir.bpm) {
      reset(); return r;
    }
    if (a) { r.bpm=r.ir.bpm; r.source=3; }
    else if (b) { r.bpm=r.red.bpm; r.source=4; }
    else { reset(); return r; }
    r.qualified=true;
    r.valid=hasCandidate_ && generation==generation_ && measuredAt>candidateAt_ &&
            measuredAt-candidateAt_<=1500 && std::fabs(r.bpm-candidateBpm_)<=.12*r.bpm;
    hasCandidate_=true; candidateAt_=measuredAt; candidateBpm_=r.bpm; generation_=generation;
    return r;
  }
  Feature analyze(const Window& input) {
    Feature f{};
    for (size_t i=0;i<400;++i) {
      if (!std::isfinite(input[i])) return f;
      raw_[i]=input[i];
    }
    double mean=0,slope=0,xx=0;
    for (size_t i=0;i<400;++i) {
      const double axis=double(i)-199.5;
      mean+=raw_[i]; slope+=axis*raw_[i]; xx+=axis*axis;
    }
    mean/=400; slope/=xx;
    double energy=0;
    for (size_t i=0;i<400;++i) {
      clean_[i]=raw_[i]-mean-(double(i)-199.5)*slope;
      energy+=clean_[i]*clean_[i];
    }
    f.amplitude=2*std::sqrt(2*energy/400);
    if (f.amplitude<4) { f.reason=Reason::LowAmplitude; return f; }
    const size_t n=detect(raw_.data(),400);
    size_t count=0;
    for (size_t i=0;i<n;++i) {
      const uint16_t p=peaks_[i];
      if (count && p-cleanPeaks_[count-1]<15) {
        if (raw_[p]>raw_[cleanPeaks_[count-1]]) cleanPeaks_[count-1]=p;
      } else {
        if (count>=cleanPeaks_.size()) return f; // Không ghi vượt workspace.
        cleanPeaks_[count++]=p;
      }
    }
    f.peaks=static_cast<uint16_t>(count);
    if (count<5) { f.reason=Reason::InsufficientBeats; return f; }
    const size_t beats=count-1;
    double sumRr=0;
    for (size_t i=0;i<beats;++i) {
      const int delta=cleanPeaks_[i+1]-cleanPeaks_[i];
      if (delta<15 || delta>75) { f.reason=Reason::RrRange; return f; }
      rr_[i]=double(delta)/50; sumRr+=rr_[i];
    }
    f.bpm=3000*double(beats)/double(cleanPeaks_[count-1]-cleanPeaks_[0]);
    const size_t recent=detect(raw_.data()+200,200);
    if (recent>=2) f.recentBpm=3000*double(recent-1)/double(peaks_[recent-1]-peaks_[0]);
    if (recent<2 || f.recentBpm<40 || f.recentBpm>200 || f.bpm<40 || f.bpm>200 ||
        std::fabs(f.bpm-f.recentBpm)>.12*f.bpm) {
      f.reason=Reason::RecentDisagreement; return f;
    }
    f.peakAge=double(399-cleanPeaks_[count-1])/50;
    for (size_t i=0;i<beats;++i) sorted_[i]=rr_[i];
    std::sort(sorted_.begin(),sorted_.begin()+beats);
    if (f.peakAge>std::min(3.,1.5*quantile(sorted_.data(),beats,.5)+.05)) {
      f.reason=Reason::StalePeak; return f;
    }
    double variance=0;
    for (size_t i=0;i<beats;++i) variance+=(rr_[i]-sumRr/beats)*(rr_[i]-sumRr/beats);
    f.rrCv=std::sqrt(variance/beats)/(sumRr/beats);
    sums_.fill(0);
    for (size_t i=0;i<beats;++i) {
      const size_t left=cleanPeaks_[i],delta=cleanPeaks_[i+1]-left;
      double center=0;
      for (size_t j=0;j<32;++j) {
        const double position=double(j)*delta/31;
        const size_t lo=static_cast<size_t>(std::floor(position));
        const size_t hi=lo<delta ? lo+1 : lo;
        const double low=raw_[left+lo]-(raw_[left]+(raw_[left+delta]-raw_[left])*double(lo)/delta);
        const double high=raw_[left+hi]-(raw_[left]+(raw_[left+delta]-raw_[left])*double(hi)/delta);
        waves_[i][j]=low+(high-low)*(position-lo); center+=waves_[i][j];
      }
      center/=32;
      double norm=0;
      for (size_t j=0;j<32;++j) { waves_[i][j]-=center; norm+=waves_[i][j]*waves_[i][j]; }
      norm=std::sqrt(norm);
      if (norm<1e-6) { f.reason=Reason::FlatBeat; return f; }
      for (size_t j=0;j<32;++j) { waves_[i][j]/=norm; sums_[j]+=waves_[i][j]; }
    }
    for (size_t i=0;i<beats;++i) {
      double dot=0,norm=0;
      for (size_t j=0;j<32;++j) {
        const double other=(sums_[j]-waves_[i][j])/double(beats-1);
        dot+=waves_[i][j]*other; norm+=other*other;
      }
      sorted_[i]=dot/std::max(1e-12,std::sqrt(norm));
    }
    std::sort(sorted_.begin(),sorted_.begin()+beats);
    f.templateMedian=quantile(sorted_.data(),beats,.5);
    f.templateP20=quantile(sorted_.data(),beats,.2);
    double total=0,pulse=0;
    // Goertzel tại đúng các bin rFFT Hann400 trong băng0,5..4Hz; không đổi ngưỡng.
    for (size_t k=4;k<=32;++k) {
      double s1=0,s2=0;
      const double coefficient=coefficients_[k-4];
      for (size_t i=0;i<400;++i) {
        const double next=clean_[i]*hann_[i]+coefficient*s1-s2;
        s2=s1; s1=next;
      }
      const double power=std::max(0.,s1*s1+s2*s2-coefficient*s1*s2);
      total+=power;
      const double frequency=double(k)*50/400;
      for (int h=1;h<=3;++h) if (std::fabs(frequency-h*f.bpm/60)<=.15) {
        pulse+=power; break;
      }
    }
    f.spectralFraction=total>0 ? pulse/total : 0;
    f.usable=true; f.reason=Reason::Computed; return f;
  }
 private:
  static constexpr double pi() { return 3.1415926535897932384626433832795; }
  static double quantile(const double* sorted,size_t n,double q) {
    const double index=(n-1)*q;
    const size_t lo=static_cast<size_t>(std::floor(index)),hi=static_cast<size_t>(std::ceil(index));
    return sorted[lo]+(sorted[hi]-sorted[lo])*(index-lo);
  }
  void windowPeaks(const double* x,size_t length,size_t offset) {
    const size_t n=(length+1)/2;
    double mean=0,slope=0,xx=0;
    for (size_t i=0;i<n;++i) {
      reduced_[i]=x[2*i]; const double axis=double(i)-double(n-1)/2;
      mean+=reduced_[i]; slope+=axis*reduced_[i]; xx+=axis*axis;
    }
    mean/=n; slope/=xx;
    for (size_t i=0;i<n;++i) reduced_[i]-=mean+(double(i)-double(n-1)/2)*slope;
    const size_t l=(n+1)/2-1;
    size_t maxScale=0;
    for (size_t k=1;k<=l;++k) if ((double(l)/k)/(double(n)/25)>=.5) maxScale=k;
    int bestCount=-1; size_t best=1;
    for (size_t k=1;k<=maxScale;++k) {
      int count=0;
      for (size_t j=k;j<n-k;++j)
        if (reduced_[j]>reduced_[j-k] && reduced_[j]>reduced_[j+k]) ++count;
      if (count>bestCount) { bestCount=count; best=k; }
    }
    kept_.fill(true);
    for (size_t k=1;k<=best;++k) for (size_t j=0;j<n;++j) {
      if (j<k || j>=n-k || !(reduced_[j]>reduced_[j-k] && reduced_[j]>reduced_[j+k])) kept_[j]=false;
    }
    for (size_t j=0;j<n;++j) if (kept_[j]) {
      const int coarse=int(2*j+1); // Giữ phép nhân chỉ số1-based từ MATLAB.
      if (coarse<3 || coarse+3>=int(length)) continue;
      size_t chosen=static_cast<size_t>(coarse-3);
      for (int p=coarse-2;p<=coarse+3;++p) if (x[p]>x[chosen]) chosen=static_cast<size_t>(p);
      flags_[offset+chosen]=true;
    }
  }
  size_t detect(const double* x,size_t n) {
    flags_.fill(false);
    if (n<=300) windowPeaks(x,n,0);
    else { windowPeaks(x,301,0); windowPeaks(x+n-301,301,n-301); }
    size_t count=0;
    for (size_t i=0;i<n;++i) if (flags_[i]) peaks_[count++]=static_cast<uint16_t>(i);
    return count;
  }
  std::array<double,400> raw_{},clean_{},hann_{};
  std::array<double,151> reduced_{};
  std::array<bool,151> kept_{};
  std::array<bool,400> flags_{};
  std::array<uint16_t,400> peaks_{};
  std::array<uint16_t,27> cleanPeaks_{};
  std::array<std::array<double,32>,26> waves_{};
  std::array<double,32> sums_{};
  std::array<double,26> rr_{},sorted_{};
  std::array<double,29> coefficients_{};
  uint64_t candidateAt_=0;
  uint32_t generation_=0;
  double candidateBpm_=0;
  bool hasCandidate_=false;
};
} // namespace asd

#include "processing/ppg_rate.h"
#include "processing/ppg_contact.h"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>

void check(bool condition, const char* reason) {
  if (!condition) { std::cerr << "FAIL: " << reason << '\n'; std::exit(1); }
}
int main(int argc, char**) {
  if (argc > 1) {
    asd::PpgRate rate; asd::PpgContact contact(10000,6000,1000);
    std::string line;
    while (std::getline(std::cin,line)) {
      std::replace(line.begin(),line.end(),',',' ');
      std::istringstream input(line); uint64_t time; uint32_t red, ir;
      if (!(input >> time >> red >> ir)) continue;
      const auto gate = contact.update(ir,time);
      if (gate.restart) rate.reset();
      if (!gate.usable) continue;
      const auto result = rate.update(ir,red,time);
      if (result.updated) std::cout << time << ',' << result.valid << ',' << result.bpm << ',' << result.periodicity
        << ',' << result.candidateBpm << ',' << result.recentBpm << ',' << result.redBpm
        << ',' << result.recentPeriodicity << ',' << result.redPeriodicity << '\n';
    }
    return 0;
  }
  unsigned cases = 0;
  for (float bpm : {40.f,60.f,100.f,150.f,180.f,200.f}) {
    asd::PpgRate rate; unsigned accepted = 0;
    for (unsigned i = 0; i < 1500; ++i) {
      const float pulse = 1800*std::sin(i*2*3.14159265f*bpm/3000);
      const auto estimate = rate.update(uint32_t(100000+pulse),uint32_t(80000+pulse*.7f),1000+i*20);
      if (estimate.updated && estimate.valid) {
        if (std::fabs(estimate.bpm-bpm) > 2) std::cerr << bpm << " -> " << estimate.bpm << '\n';
        check(std::fabs(estimate.bpm-bpm) <= 2,"clean periodic input rate"); ++accepted;
      }
    }
    if (accepted < 15) std::cerr << "rate=" << bpm << " accepted=" << accepted << '\n';
    check(accepted >= 15,"clean periodic input availability"); ++cases;
  }
  for (unsigned kind = 0; kind < 4; ++kind) {
    asd::PpgRate rate; uint32_t random = 17; unsigned accepted = 0;
    float drift = 0;
    for (unsigned i = 0; i < 3000; ++i) {
      random = random*1664525u + 1013904223u;
      const float noise = (float(random>>8)/16777216-.5f)*1000;
      drift = .97f*drift + noise*.03f;
      const float signal = kind == 0 ? 0 : kind == 1 ? noise : kind == 2 ? drift : float(i)*2;
      const auto e = rate.update(uint32_t(100000+signal),uint32_t(80000+signal*.8f),1000+i*20);
      if (e.updated && e.valid) ++accepted;
    }
    check(accepted == 0,"flat/noise/random drift/ramp became HR"); ++cases;
  }
  {
    asd::PpgRate rate;
    for (unsigned i = 0; i < 1500; ++i) {
      const float phase = i*2*3.14159265f*80/3000;
      const float pulse = 1800*std::sin(phase)+1000*std::sin(2*phase);
      const auto e = rate.update(uint32_t(100000+pulse),uint32_t(80000+pulse*.8f),1000+i*20);
      if (e.updated && e.valid) check(std::fabs(e.bpm-80)<3,"second harmonic doubled HR");
    }
    check(rate.estimate().valid,"pulse with secondary peak lost"); ++cases;
  }
  {
    asd::PpgRate rate;
    for (unsigned i = 0; i < 1500; ++i) {
      const float ir = 1800*std::sin(i*2*3.14159265f*80/3000);
      const float red = 1200*std::sin(i*2*3.14159265f*130/3000);
      check(!rate.update(uint32_t(100000+ir),uint32_t(80000+red),1000+i*20).valid,
            "disagreeing optical channels accepted");
    }
    ++cases;
  }
  {
    asd::PpgRate rate;
    for (unsigned i = 0; i < 1500; ++i) {
      const float pulse = 1800*std::sin(i*2*3.14159265f/50);
      (void)rate.update(uint32_t(100000+pulse),uint32_t(80000+pulse*.8f),1000+i*20);
    }
    check(rate.estimate().valid,"precondition before gap");
    check(!rate.update(100000,80000,40000).valid,"sample gap held previous estimate"); ++cases;
  }
  {
    asd::PpgRate rate; float phase = 0;
    for (unsigned i = 0; i < 2100; ++i) {
      phase += 2*3.14159265f*(i < 1500 ? 60 : 120)/3000;
      const float pulse = 1800*std::sin(phase);
      (void)rate.update(uint32_t(100000+pulse),uint32_t(80000+pulse*.8f),1000+i*20);
    }
    check(rate.estimate().valid && std::fabs(rate.estimate().bpm-120)<3,
          "new frequency not acquired within12s"); ++cases;
    for (unsigned i = 2100; i < 2350; ++i) (void)rate.update(100000,80000,1000+i*20);
    check(!rate.estimate().valid,"flat tail kept old HR alive"); ++cases;
  }
  {
    asd::PpgRate rate;
    for (unsigned i = 0; i < 1500; ++i) {
      const float phase = i*2*3.14159265f/50;
      const float slow = 1200*std::sin(i*2*3.14159265f*.12f/50);
      const float pulse = 1800*std::sin(phase);
      (void)rate.update(uint32_t(100000+pulse+slow),uint32_t(80000+pulse*.8f+slow),1000+i*20);
    }
    check(rate.estimate().valid && std::fabs(rate.estimate().bpm-60)<3,
          "slow baseline drift changed pulse rate"); ++cases;
  }
  for (unsigned mode = 0; mode < 4; ++mode) {
    asd::PpgRate rate; unsigned accepted = 0; uint32_t random = 71;
    for (unsigned i = 0; i < 1500; ++i) {
      random = random*1664525u + 1013904223u;
      const float noise = (float(random>>8)/16777216-.5f)*6;
      const float pulse = std::sin(i*2*3.14159265f*80/3000);
      const float ir = mode == 1 ? 0 : mode == 2 ? noise*100 : pulse*8+noise;
      const float red = mode == 3 ? 0 : pulse*12;
      const auto e = rate.update(uint32_t(100000+ir),uint32_t(80000+red),1000+i*20);
      if (e.updated && e.valid) {
        check(std::fabs(e.bpm-80)<3,"weak pulse/alternate channel wrong rate");
        if (mode == 1 || mode == 2) check(e.source==2,"RED did not replace unusable IR");
        if (mode == 3) check(e.source==1,"IR did not survive unusable RED");
        ++accepted;
      }
    }
    check(accepted>=15,"low-amplitude genuine pulse lost"); ++cases;
  }
  {
    asd::PpgRate rate;
    for (unsigned i = 0; i < 1500; ++i) {
      const float pulse = .4f*std::sin(i*2*3.14159265f/50);
      check(!rate.update(uint32_t(100000+pulse),uint32_t(80000+pulse),1000+i*20).valid,
            "sub-quantization waveform accepted");
    }
    ++cases;
  }
  unsigned noiseWindows=0, falseWindows=0;
  for (unsigned kind=0; kind<4; ++kind) {
    for (uint32_t seed=1; seed<=12; ++seed) {
      asd::PpgRate rate; uint32_t random=seed; float ir=0,red=0;
      const float memory = kind==0 ? 0 : kind==1 ? .85f : kind==2 ? .97f : .995f;
      for (unsigned i=0; i<3000; ++i) {
        random=random*1664525u+1013904223u;
        const float a=(float(random>>8)/16777216-.5f)*1000;
        random=random*1664525u+1013904223u;
        const float b=(float(random>>8)/16777216-.5f)*1000;
        ir=memory*ir+(1-memory)*a; red=memory*red+(1-memory)*b;
        const auto e=rate.update(uint32_t(100000+ir),uint32_t(80000+red),1000+i*20);
        if (e.updated) { ++noiseWindows; if (e.valid) ++falseWindows; }
      }
      ++cases;
    }
  }
  std::cout << "Noise-only benchmark: " << falseWindows << '/' << noiseWindows << " windows accepted\n";
  check(falseWindows*100 <= noiseWindows,"noise-only acceptance exceeds1percent development limit");
  {
    asd::PpgRate rate;
    for (unsigned i=0; i<2000; ++i) {
      const uint32_t level=i<500 ? 100000 : i<1000 ? 130000 : 90000;
      check(!rate.update(level,level*4/5,1000+i*20).valid,"pressure DC steps became HR");
    }
    ++cases;
  }
  {
    asd::PpgRate rate; unsigned updates=0;
    for (unsigned i=0; i<600; ++i) {
      const float pulse=1800*std::sin(i*2*3.14159265f/50);
      const auto e=rate.update(uint32_t(100000+pulse),uint32_t(80000+pulse*.8f),1000+i*20);
      if (e.updated && ++updates==1) check(!e.valid,"single good window bypassed confirmation");
    }
    check(updates>=2 && rate.estimate().valid,"second matching window failed to confirm"); ++cases;
  }
  for (float bpm : {80.f,90.f,100.f,120.f,160.f}) {
    asd::PpgRate rate;
    for (unsigned i=0; i<1500; ++i) {
      const float phase=i*2*3.14159265f*bpm/3000;
      // Biên độ luân phiên lớn/nhỏ nhưng mỗi chu kỳ vẫn có một xung thật.
      const float pulse=1800*(.65f+.35f*std::cos(phase*.5f))*std::sin(phase);
      (void)rate.update(uint32_t(100000+pulse),uint32_t(80000+pulse*.8f),1000+i*20);
    }
    if (!rate.estimate().valid || std::fabs(rate.estimate().bpm-bpm)>3)
      std::cerr << "Alternating pulse expected=" << bpm << " actual=" << rate.estimate().bpm << '\n';
    check(rate.estimate().valid && std::fabs(rate.estimate().bpm-bpm)<3,
          "alternating pulse amplitude caused half-rate lock"); ++cases;
  }
  std::cout << "PASS: " << cases << " window HR cases\n";
}

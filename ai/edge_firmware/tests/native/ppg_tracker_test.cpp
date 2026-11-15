#include "processing/ppg_cycle_tracker.h"
#include "processing/ppg_rate.h"
#include "processing/ppg_contact.h"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

void check(bool ok,const char* why) { if(!ok) {std::cerr<<"FAIL: "<<why<<'\n';std::exit(1);} }
asd::PpgCycleTracker::Window wave(float bpm,unsigned second=0,float amplitude=100) {
  asd::PpgCycleTracker::Window x{};
  for(size_t i=0;i<400;++i) x[i]=amplitude*std::sin((i+second*50)*2*3.14159265358979323846f*bpm/3000);
  return x;
}
int main(int argc,char**) {
  if(argc>1) {
    asd::PpgRate base;
    asd::PpgContact contact(10000,6000,1000);asd::PpgCycleTracker tracker;
    uint32_t generation=0;std::string line;
    std::cout<<std::setprecision(9);
    while(std::getline(std::cin,line)) {
      std::replace(line.begin(),line.end(),',',' ');
      std::istringstream in(line);uint64_t at;uint32_t ir,red;
      if(!(in>>at>>red>>ir)) continue;
      auto gate=contact.update(ir,at);
      if(gate.restart || ir==0x3ffff || red==0x3ffff) {base.reset();tracker.reset();++generation;}
      if(!gate.usable || ir==0x3ffff || red==0x3ffff) continue;
      auto b=base.update(ir,red,at);
      if(!b.updated) continue;
      asd::PpgCycleTracker::Window a{},c{};
      if(!base.copyFilteredWindow(a,c)) continue;
      auto r=tracker.update(a,c,at,generation);
      std::cout<<at<<','<<r.valid<<','<<r.bpm<<','<<r.massScore<<','<<r.evidence<<','
               <<b.valid<<','<<b.bpm<<','<<r.rawBpm<<'\n';
    }
    return 0;
  }
  unsigned cases=0;
  for(float bpm:{40.f,60.f,80.f,100.f,150.f,180.f,200.f}) {
    asd::PpgCycleTracker tracker;unsigned accepted=0;
    for(unsigned i=0;i<20;++i) {
      auto x=wave(bpm,i);auto y=x;for(float&v:y)v*=.7f;
      const auto r=tracker.update(x,y,10000+i*1000,1);
      if(r.valid) {check(std::fabs(r.bpm-bpm)<3,"clean rate drift/half/double");++accepted;}
      check(r.measuredAt==10000+i*1000,"timestamp changed");
    }
    if(accepted<17) std::cerr<<"clean rate="<<bpm<<" accepted="<<accepted<<'\n';
    check(accepted>=17,"clean coverage too low");++cases;
    auto flat=asd::PpgCycleTracker::Window{};
    check(!tracker.update(flat,flat,30000,1).valid,"flat input predicted an HR");++cases;
    check(!tracker.update(wave(bpm),wave(bpm),31000,1).valid,"flat input did not clear confirmation");++cases;
  }
  for(int type=0;type<3;++type) {
    asd::PpgCycleTracker tracker;auto x=wave(80);
    (void)tracker.update(x,x,10000,1);check(tracker.update(x,x,11000,1).valid,"precondition");
    auto r=tracker.update(x,x,type==0 ? 11000 : type==1 ? 13000 : 12000,type==2 ? 2 : 1);
    check(!r.valid,"clock/age/generation did not reset tracker");++cases;
  }
  {
    asd::PpgCycleTracker tracker;auto a=wave(80),b=wave(40);
    check(!tracker.update(a,a,10000,1).valid,"first window should not confirm");
    const auto changed=tracker.update(b,b,11000,1);
    check(!changed.valid,"startup confirmed two high-quality but conflicting rates");++cases;
    asd::PpgCycleTracker reverse;
    reverse.update(b,b,10000,1);
    check(!reverse.update(a,a,11000,1).valid,"startup harmonic confirmation depends on order");++cases;
  }
  for(float bpm:{35.f,205.f}) {
    asd::PpgCycleTracker tracker;unsigned accepted=0;
    for(unsigned second=0;second<20;++second) {
      auto x=wave(bpm,second);accepted+=tracker.update(x,x,10000+1000*second,1).valid;
    }
    check(accepted==0,"outside-range periodic signal clamped to a boundary HR");++cases;
  }
  for(float bpm:{48.f,80.f,110.f}) {
    asd::PpgCycleTracker tracker;asd::PpgCycleTracker::Result r{};
    for(unsigned second=0;second<15;++second) {
      auto x=wave(bpm,second);
      for(size_t i=0;i<400;++i) {
        const float phase=(i+second*50)*2*3.14159265358979323846f*bpm/3000;
        x[i]+=130*std::sin(2*phase+.3f);
      }
      r=tracker.update(x,x,10000+1000*second,1);
    }
    check(r.valid && std::fabs(r.bpm-bpm)<4,"strong harmonic caused half/double lock");++cases;
  }
  for(float bpm:{72.f,100.f,150.f}) {
    asd::PpgCycleTracker tracker;asd::PpgCycleTracker::Result r{};
    for(unsigned second=0;second<25;++second) {
      auto x=wave(bpm,second);
      for(size_t i=0;i<400;++i) {
        const float phase=(i+second*50)*2*3.14159265358979323846f*bpm/3000;
        x[i]*=(.65f+.35f*std::cos(.5f*phase));
      }
      r=tracker.update(x,x,10000+1000*second,1);
    }
    check(r.valid && std::fabs(r.bpm-bpm)<4,"alternating amplitude locked to doubled period");++cases;
  }
  {
    asd::PpgRate filter;asd::PpgCycleTracker tracker;unsigned accepted=0;
    for(unsigned i=0;i<3000;++i) {
      const double seconds=i/50.;
      const double pulse=100*std::sin(2*3.14159265358979323846*80*seconds/60);
      const double drift=300*std::sin(2*3.14159265358979323846*.2*seconds);
      auto e=filter.update(uint32_t(100000+pulse+drift),uint32_t(80000+.7*pulse+.8*drift),1000+i*20);
      if(!e.updated)continue;
      asd::PpgCycleTracker::Window a{},b{};if(!filter.copyFilteredWindow(a,b))continue;
      auto r=tracker.update(a,b,e.measuredAt,1);
      if(r.valid){check(std::fabs(r.bpm-80)<5,"slow baseline drift became a low-rate pulse");++accepted;}
    }
    check(accepted>=20,"drift fixture passed only by rejecting all pulse windows");++cases;
  }
  {
    asd::PpgCycleTracker tracker;auto a=wave(80),b=wave(130);
    for(unsigned i=0;i<10;++i) check(!tracker.update(a,b,10000+1000*i,1).valid,"clear conflicting channels accepted");
    ++cases;
  }
  {
    asd::PpgCycleTracker tracker;asd::PpgCycleTracker::Result r{};
    for(unsigned i=0;i<30;++i) {auto x=wave(i<15 ? 80.f : 120.f,i);r=tracker.update(x,x,10000+i*1000,1);}
    check(r.valid && std::fabs(r.bpm-120)<4,"tracker permanently locked to previous HR");++cases;
  }
  for(bool rising:{false,true}) {
    const float before=rising ? 40.f : 80.f,after=rising ? 80.f : 40.f;
    asd::PpgCycleTracker tracker;unsigned switched=0;
    for(unsigned i=0;i<15;++i){auto x=wave(before,i);(void)tracker.update(x,x,10000+i*1000,1);}
    for(unsigned i=0;i<30;++i){
      auto x=wave(after,15+i);auto r=tracker.update(x,x,25000+i*1000,1);
      if(r.valid && std::fabs(r.rawBpm-after)<3){
        check(std::fabs(r.bpm-after)<3,"confirmed track switch reused the previous track smoother");++switched;
      }
    }
    check(switched>5,"track-switch test passed only by suppressing all new-track outputs");++cases;
  }
  {
    asd::PpgCycleTracker tracker;unsigned filtered=0;
    for(unsigned i=0;i<30;++i) {
      // Kiểm làm mượt biến động nhỏ trong cùng quỹ đạo; nhảy lớn được kiểm riêng.
      auto x=wave(i<15 ? 80.f : 88.f,i);auto r=tracker.update(x,x,10000+i*1000,1);
      if(r.valid && std::fabs(r.bpm-r.rawBpm)>.05f) ++filtered;
      if(r.valid) check(r.measuredAt==10000+i*1000,"smoother timestamp is not current evidence time");
    }
    check(filtered>0,"test did not exercise smoothing a new rate");++cases;
    tracker.reset();auto a=wave(160);tracker.update(a,a,50000,2);
    auto r=tracker.update(a,a,51000,2);
    check(r.valid && std::fabs(r.bpm-160)<3,"new contact inherited previous smoothing state");++cases;
  }
  {
    asd::PpgCycleTracker tracker;auto x=wave(80),flat=asd::PpgCycleTracker::Window{};
    tracker.update(x,flat,10000,1);auto r=tracker.update(x,flat,11000,1);
    check(r.valid && r.source==6 && std::fabs(r.bpm-80)<3,"flat RED blocked valid IR");++cases;
    x[0]=NAN;
    check(!tracker.update(x,flat,12000,1).valid,"invalid channel retained old HR");++cases;
  }
  {
    asd::PpgCycleTracker tracker;
    for(unsigned i=0;i<15;++i) {auto x=wave(80,i);(void)tracker.update(x,x,10000+i*1000,1);}
    auto low=wave(40);
    const auto first=tracker.update(low,low,25000,1);
    check(!first.valid || first.rawBpm>55,"single half-rate window immediately replaced anchor");++cases;
    unsigned lowAccepted=0;
    for(unsigned i=1;i<30;++i) {auto x=wave(40,i);auto r=tracker.update(x,x,25000+i*1000,1);
      if(r.valid && std::fabs(r.bpm-40)<3) ++lowAccepted;}
    check(lowAccepted>5,"persistent real40bpm was permanently blocked");++cases;
  }
  {
    asd::PpgCycleTracker tracker;auto flat=asd::PpgCycleTracker::Window{};
    for(unsigned i=0;i<15;++i) {auto x=wave(108,i);(void)tracker.update(x,x,10000+i*1000,1);}
    check(!tracker.update(flat,flat,25000,1).valid,"weak window emitted an old HR");
    for(unsigned i=0;i<5;++i) {
      auto x=wave(54,16+i);const auto r=tracker.update(x,x,26000+i*1000,1);
      check(!r.valid || r.rawBpm>70,"one weak window erased the half-rate change guard");
    }
    unsigned accepted=0;
    for(unsigned i=5;i<35;++i) {
      auto x=wave(54,16+i);const auto r=tracker.update(x,x,26000+i*1000,1);
      if(r.valid && std::fabs(r.bpm-54)<3) ++accepted;
    }
    check(accepted>5,"a genuinely changed low rate was permanently blocked after weak data");++cases;
  }
  std::cout<<"PASS: "<<cases<<" tracker cases; workspace="<<sizeof(asd::PpgCycleTracker)<<" bytes\n";
}

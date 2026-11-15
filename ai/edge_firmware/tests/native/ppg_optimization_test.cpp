#include "processing/ppg_exposure.h"
#include "processing/ppg_cycle_tracker.h"
#include <cstdlib>
#include <iostream>
#include <random>

void require(bool ok,const char* why){if(!ok){std::cerr<<"FAIL: "<<why<<'\n';std::exit(1);}}
constexpr float pi=3.14159265358979323846f;
using Window=asd::PpgCycleTracker::Window;
Window pulse(float bpm,unsigned second,float amplitude=100){
  Window x{};for(size_t i=0;i<400;++i)x[i]=amplitude*std::sin(2*pi*bpm*(i+50*second)/3000);
  return x;
}
int main(){
  unsigned checks=0;
  {
    asd::PpgExposure gain;gain.begin(0,255,0);
    require(gain.red()==100 && gain.ir()==16,"initial configuration bypassed bounded LED range");++checks;
  }
  {
    asd::PpgExposure gain;gain.begin(0);
    for(uint64_t t=20;t<=2000;t+=20)gain.observe(900,800,false);
    require(!gain.decide(2000,false,true).changed,"AGC boosted air/no contact");++checks;
    for(unsigned cycle=0;cycle<12;++cycle){
      for(unsigned i=0;i<50;++i)gain.observe(5000,10000,false);
      const uint64_t at=3000+cycle*21000;
      auto d=gain.decide(at,true,true);
      require(d.red<=100 && d.ir<=100 && d.red>=16 && d.ir>=16,"AGC exceeded current limits");
      if(d.changed){gain.commit(at,d.red,d.ir);require(!gain.decide(at+100,true,true).changed,"AGC oscillated during hold");}
    }
    require(gain.red()==100 && gain.ir()==100,"bounded startup gain never reached ceiling");++checks;
    gain.tracked(260000);
    for(unsigned i=0;i<50;++i)gain.observe(3000,3000,false);
    require(!gain.decide(261000,true,true).changed,"AGC raised light despite fresh tracked HR");++checks;
    for(unsigned i=0;i<50;++i)gain.observe(250000,80000,true);
    const auto d=gain.decide(290000,true,false);
    require(d.changed && d.red<100 && d.ir<100,"overload did not reduce light");++checks;
  }
  {
    asd::PpgExposure gain;gain.begin(0);
    for(unsigned i=0;i<200;++i)gain.observe(900,900,false,false);
    for(unsigned i=0;i<10;++i)gain.observe(150000,150000,false,true);
    require(!gain.decide(4200,true,true).changed,"AGC raised current from air samples mixed with new contact");++checks;
    gain.commit(5000,60,60);gain.tracked(5000);
    for(unsigned i=0;i<50;++i)gain.observe(262143,262143,true,false);
    auto d=gain.decide(6000,false,false);
    require(d.changed && d.red<60,"saturation waited for normal 20-second hold");++checks;
  }
  {
    asd::PpgMotionHistory h;asd::PpgMotionSample s{};s.valid=true;s.at=1000;h.add(s);
    require(h.nearest(1025).valid && !h.nearest(1026).valid,"IMU alignment accepted stale reference");++checks;
    s.at=10;h.add(s);require(!h.nearest(1000).valid,"IMU history crossed clock rollback");++checks;
  }
  {
    asd::PpgCycleTracker clean,damaged;
    std::mt19937 rng(20261114);std::normal_distribution<float> noise(0,200);
    float cleanSqi=0,weakSqi=0;unsigned cleanCount=0,weakCount=0;
    for(unsigned second=0;second<25;++second){
      auto x=pulse(80,second);auto y=x;for(float&v:y)v*=.7f;
      auto r=clean.update(x,y,10000+1000*second,1);
      if(r.valid){cleanSqi+=r.sqi;++cleanCount;}
      for(float&v:y)v=noise(rng); // K?nh RED nhi?u kh?ng ???c ch?n IR r?.
      auto q=damaged.update(x,y,10000+1000*second,1);
      if(q.valid){require(std::fabs(q.bpm-80)<4,"noisy RED pulled HR away from clear IR");weakSqi+=q.sqi;++weakCount;}
    }
    require(cleanCount>=20 && weakCount>=15,"channel selection only passed by withholding HR");
    require(cleanSqi/cleanCount>weakSqi/weakCount,"SQI ignored channel agreement");checks+=2;
    std::cout<<"clean_sqi="<<cleanSqi/cleanCount<<" single_channel_sqi="<<weakSqi/weakCount<<'\n';
  }
  {
    asd::PpgCycleTracker raw,compensated;unsigned rawWrong=0,cleanRight=0,used=0;
    float residual=0;
    for(unsigned second=0;second<35;++second){
      auto heart=pulse(80,second),artifact=pulse(132,second,250);Window ir{},red{};
      asd::PpgMotionWindow motion{};
      for(size_t i=0;i<400;++i){
        ir[i]=heart[i]+artifact[i];red[i]=.7f*heart[i]+.8f*artifact[i];
        motion.axes[0][i]=artifact[i]/1000;motion.valid[i]=true;
      }
      auto a=raw.update(ir,red,10000+1000*second,1);
      auto b=compensated.update(ir,red,10000+1000*second,1,&motion);
      if(a.valid && std::fabs(a.bpm-80)>10)++rawWrong;
      if(b.valid){require(std::fabs(b.bpm-80)<5,"motion correction selected cadence");++cleanRight;}
      used+=b.motionCorrected;
      asd::PpgMotionCleaner cleaner;cleaner.prepare(ir,red,&motion);residual=cleaner.residualIr;
    }
    std::cout<<"motion raw_wrong="<<rawWrong<<" corrected_right="<<cleanRight<<" cleaned_windows="<<used<<" residual="<<residual<<'\n';
    require(rawWrong>=10 && cleanRight>=15 && used>=15,"motion fixture not actually improved");++checks;
  }
  {
    asd::PpgCycleTracker tracker;unsigned accepted=0;
    for(unsigned second=0;second<20;++second){
      auto x=pulse(100,second);asd::PpgMotionWindow motion{};
      for(size_t i=0;i<400;++i){motion.axes[0][i]=x[i]/1000;motion.valid[i]=true;}
      accepted+=tracker.update(x,x,10000+second*1000,1,&motion).valid;
    }
    require(accepted==0,"pure motion or pulse/cadence overlap claimed as confirmed HR");++checks;
    asd::PpgCycleTracker noReference;auto x=pulse(80,0);asd::PpgMotionWindow invalid{};
    for(auto&axis:invalid.axes)axis.fill(1);
    noReference.update(x,x,10000,1,&invalid);
    auto r=noReference.update(x,x,11000,1,&invalid);
    require(r.valid && !r.motionSupported && r.motionCoverage==0,"missing reference fabricated motion correction");++checks;
  }
  std::cout<<"PASS: "<<checks<<" optimization scenarios\n";
}

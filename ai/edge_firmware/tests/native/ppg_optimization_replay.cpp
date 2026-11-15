#include "processing/ppg_rate.h"
#include "processing/ppg_contact.h"
#include "processing/ppg_cycle_tracker.h"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

int main(){
  asd::PpgRate rate;asd::PpgCycleTracker tracker;
  asd::PpgContact contact(2500,1800,1000);
  uint32_t generation=0;int previousExposure=-1;std::string line;
  std::cout<<std::setprecision(9);
  while(std::getline(std::cin,line)){
    std::replace(line.begin(),line.end(),',',' ');
    std::istringstream in(line);uint64_t at;uint32_t red,ir;
    if(!(in>>at>>red>>ir))continue;
    std::array<float,6> axes{};for(float& v:axes)if(!(in>>v))v=0;
    bool aligned=false;int exposure=0;in>>aligned>>exposure;
    const auto gate=contact.update(ir,at);
    if(gate.restart || red==0x3ffff || ir==0x3ffff || exposure!=previousExposure){
      rate.reset();tracker.reset();++generation;previousExposure=exposure;
    }
    if(!gate.usable || red==0x3ffff || ir==0x3ffff)continue;
#ifdef PPG_OPTIMIZATION_V2
    asd::PpgMotionSample reference{at,axes,aligned};
    const auto e=rate.update(ir,red,at,&reference);
#else
    const auto e=rate.update(ir,red,at);
#endif
    if(!e.updated)continue;
    asd::PpgCycleTracker::Window a{},b{};if(!rate.copyFilteredWindow(a,b))continue;
#ifdef PPG_OPTIMIZATION_V2
    asd::PpgMotionWindow motion;rate.copyMotionWindow(motion);
    const auto r=tracker.update(a,b,at,generation,&motion);
    std::cout<<at<<','<<r.valid<<','<<r.bpm<<','<<r.sqi<<','<<r.motionCoverage<<','<<r.motionOverlap<<','<<r.motionCorrected<<','<<unsigned(r.source)<<'\n';
#else
    const auto r=tracker.update(a,b,at,generation);
    std::cout<<at<<','<<r.valid<<','<<r.bpm<<','<<r.evidence<<",0,0,0,"<<unsigned(r.source)<<'\n';
#endif
  }
}

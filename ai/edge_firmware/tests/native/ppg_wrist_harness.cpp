// Offline only: actual driver + quality policy; no MQTT or hardware claims.
#include "MAX30102Sensor.h"
#include "Wire.h"
#include "processing/ppg_wrist_motion.h"
#include <iostream>
#include <iomanip>

namespace {
asd::PpgQuality quality;
asd::PpgHybridResult visible{},pending{};
uint64_t availableAt=0;
bool queued=false;
}
namespace asd {
bool ppgHybridSetup(){return true;}
bool ppgHybridSubmit(const PpgRate& rate,uint64_t at,uint32_t generation) {
  PpgQuality::Window ir{},red{};
  if (!rate.copyFilteredWindow(ir,red)) return false;
  pending={};pending.analysis=quality.update(ir,red,at,generation);
  // Model an asynchronous 150ms worker; not an ESP CPU timing measurement.
  availableAt=fakeNowMs+150;queued=true;return true;
}
bool ppgHybridLatest(PpgHybridResult& result) {
  if (queued && fakeNowMs>=availableAt){visible=pending;queued=false;}
  result=visible;return true;
}
PpgHybridStats ppgHybridStats(){return {};}
}
int main() {
  MAX30102Sensor sensor;(void)sensor.begin();
  for(unsigned i=0;i<30 && sensor.isInitializing();++i){fakeNowMs+=10;(void)sensor.read();}
  if (!sensor.isReady()) return 2;
  asd::WristMotionGuard motion;
  uint64_t at;uint32_t red,ir;unsigned ambient;float motionScore;
  while(std::cin>>at>>red>>ir>>ambient>>motionScore) {
    fakeNowMs=at;Wire.registers[0x00]=ambient ? 0x20 : 0;
    Wire.pushPpg(red,ir);auto r=sensor.read();
    motion.update(at,at,true,true,true,motionScore);
    if (!motion.allowsHr()) {r.valid=false;r.hasHeartRateTimestamp=false;r.heartRate=0;}
    std::cout<<at<<','<<r.valid<<','<<std::setprecision(9)<<r.heartRate<<','
      <<unsigned(r.heartRateSource)<<','<<r.heartRateMonotonicMs<<','
      <<r.opticalOverload<<','<<r.contactSettled<<'\n';
  }
}

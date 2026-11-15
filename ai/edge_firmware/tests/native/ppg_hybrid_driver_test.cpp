#include "MAX30102Sensor.h"
#include "Wire.h"
#include <cstdlib>
#include <iostream>

namespace {
asd::PpgHybridResult fakeResult{};
uint32_t submittedGeneration=0;
bool available=false;
unsigned resultReads=0;
constexpr uint8_t workerSource=ASD_PPG_TRACKER_ENABLED ? 5 : 3;
void check(bool ok,const char* why) { if(!ok){std::cerr<<"FAIL: "<<why<<'\n';std::exit(1);} }
MAX30102Data step(MAX30102Sensor& s,uint32_t ir=100000,uint32_t red=80000) {
  fakeNowMs+=20; Wire.pushPpg(red,ir); return s.read();
}
void publishFake(uint32_t generation,double bpm,bool valid=true) {
  available=true; fakeResult={}; fakeResult.analysis.valid=valid;
  fakeResult.analysis.bpm=bpm; fakeResult.analysis.source=workerSource;
  fakeResult.analysis.generation=generation; fakeResult.analysis.measuredAt=fakeNowMs-200;
  fakeResult.analysis.sqi=.8f;
}
}
namespace asd {
bool ppgHybridSetup(){return true;}
bool ppgHybridSubmit(const PpgRate& rate,uint64_t,uint32_t generation) {
  PpgQuality::Window ir{},red{};check(rate.copyFilteredWindow(ir,red),"missing producer snapshot");
  submittedGeneration=generation;return true;
}
bool ppgHybridLatest(PpgHybridResult& r){++resultReads;if(!available)return false;r=fakeResult;return true;}
PpgHybridStats ppgHybridStats(){return {};}
}
int main() {
  MAX30102Sensor sensor;(void)sensor.begin();
  for(unsigned i=0;i<30 && sensor.isInitializing();++i){fakeNowMs+=10;(void)sensor.read();}
  check(sensor.isReady(),"sensor startup");
  MAX30102Data reading{};
  for(unsigned i=0;i<750;++i) {
    const double wave=std::sin(i*2*3.14159265358979323846*80/3000);
    reading=step(sensor,uint32_t(100000+1800*wave),uint32_t(80000+1200*wave));
  }
  check(reading.valid && submittedGeneration!=0 && reading.heartRateSource==8 &&
        std::fabs(reading.heartRate-80)<3,"RR primary did not acquire clean input");
  const auto primaryRate=reading.heartRate;
  const auto primaryAt=reading.heartRateMonotonicMs;
  publishFake(submittedGeneration,120);
  const auto readsBefore=resultReads;
  reading=sensor.read();
  check(resultReads==readsBefore+1 && std::fabs(reading.qualityEvidence-.8f)<.001f,
        "quality snapshot was not read consistently");
  check(reading.valid && reading.heartRate==primaryRate && reading.heartRateSource==8 &&
        reading.heartRateMonotonicMs==primaryAt,"quality worker overwrote RR primary HR");
  const auto count=reading.acceptedWindows;
  reading=sensor.read();
  check(reading.acceptedWindows==count && reading.heartRateMonotonicMs==primaryAt,
        "cache renewed measurement timestamp or counted the beat twice");
  available=false;
  for(unsigned i=0;i<350;++i)reading=step(sensor);
  check(!reading.valid && !reading.hasHeartRateTimestamp,"flat input kept stale HR");
  publishFake(submittedGeneration,72);
  reading=sensor.read();
  check(!reading.valid && !reading.hasHeartRateTimestamp,
        "quality worker fabricated HR without a fresh RR beat");
  for(unsigned i=0;i<400;++i) {
    const double wave=std::sin(i*2*3.14159265358979323846*80/3000);
    reading=step(sensor,uint32_t(100000+1800*wave),uint32_t(80000+1200*wave));
  }
  check(reading.valid && reading.heartRateSource==8,"RR failed to reacquire after flat input");
  const auto oldGeneration=submittedGeneration;
  for(unsigned i=0;i<12;++i)reading=step(sensor,1000,1000);
  check(!reading.valid && !reading.fingerDetected,"contact loss kept HR");
  for(unsigned i=0;i<100;++i)reading=step(sensor);
  publishFake(oldGeneration,72);
  check(!sensor.read().valid,"old worker result supplied HR after recontact");
  Wire.failedRegister=0x00;
  reading=step(sensor);
  check(!reading.valid && !reading.hasHeartRateTimestamp && !sensor.isReady(),"I2C error retained HR");

  available=false;Wire=TwoWire{};fakeNowMs=0;MAX30102Sensor adaptive;
  (void)adaptive.begin();for(unsigned i=0;i<30 && adaptive.isInitializing();++i){fakeNowMs+=10;(void)adaptive.read();}
  adaptive.setExposureQuiet(true);
  bool observedChange=false;
  for(unsigned i=0;i<450;++i){
    reading=step(adaptive,5000,100000);
    if(reading.exposureChanges){observedChange=true;break;}
  }
  check(observedChange && Wire.registers[0x0c]==50 && Wire.registers[0x0d]==60,
        "actual driver did not independently adjust weak IR and retain RED");
  check(!reading.valid,"mixed-exposure FIFO produced HR before fresh analysis");
  Wire.failedWriteRegister=0x0d;
  for(unsigned i=0;i<1500 && adaptive.isReady();++i)reading=step(adaptive,5000,100000);
  check(!adaptive.isReady() && !reading.valid && adaptive.acquisitionStats().lastFault.reg==0x0d &&
        adaptive.acquisitionStats().lastFault.kind==PpgFaultKind::Transmit,
        "AGC I2C write error lost exact register or retained HR");
  Wire=TwoWire{};fakeNowMs=0;MAX30102Sensor corrupt;
  (void)corrupt.begin();for(unsigned i=0;i<30 && corrupt.isInitializing();++i){fakeNowMs+=10;(void)corrupt.read();}
  corrupt.setExposureQuiet(true);Wire.corruptRegister=0x0d;
  for(unsigned i=0;i<450 && corrupt.isReady();++i)reading=step(corrupt,5000,100000);
  check(!corrupt.isReady() && !reading.valid && corrupt.acquisitionStats().lastFault.reg==0x0d &&
        corrupt.acquisitionStats().lastFault.expected==60,
        "AGC readback mismatch accepted unconfirmed current");
  std::cout<<"PASS: RR-primary, quality-only worker and actual MAX30102/AGC integration cases (fake transport result, no hardware)\n";
}

#pragma once
#include <algorithm>
#include <cstdint>

namespace asd {
// MAX30102 LEDx_PA: ~0.2 mA/count. Giới hạn thử nghiệm 3.2..20 mA,
// không tự tăng khi hở da/chuyển động. Không gọi I2C trong bộ điều khiển này.
class PpgExposure {
 public:
  struct Decision { bool changed=false; uint8_t red=50,ir=50; };
  void begin(uint64_t now,uint8_t red=50,uint8_t ir=50) {
    red_=uint8_t(std::max(16,std::min(100,int(red))));
    ir_=uint8_t(std::max(16,std::min(100,int(ir))));
    lastChange_=now;changes_=0;hasTracked_=false;resetWindow();
  }
  void resetWindow() {count_=stableCount_=0;redSum_=irSum_=stableRedSum_=stableIrSum_=0;overload_=false;}
  void observe(uint32_t red,uint32_t ir,bool overload,bool stable=true) {
    redSum_+=red;irSum_+=ir;++count_;overload_|=overload;
    if(stable){stableRedSum_+=red;stableIrSum_+=ir;++stableCount_;}
    else {stableCount_=0;stableRedSum_=stableIrSum_=0;}
  }
  void tracked(uint64_t now){lastTracked_=now;hasTracked_=true;}
  Decision decide(uint64_t now,bool contact,bool quiet) {
    Decision d{false,red_,ir_};
    const uint64_t hold=overload_ || (changes_<5 && !hasTracked_)?1000u:20000u;
    if(now<lastChange_ || now-lastChange_<hold || count_<50) return d;
    const bool stable=stableCount_>=50;
    const uint32_t red=stable?stableRedSum_/stableCount_:redSum_/count_;
    const uint32_t ir=stable?stableIrSum_/stableCount_:irSum_/count_;
    const bool overload=overload_;resetWindow();
    // Tăng chỉ khi có tiếp xúc đã xác nhận; giảm vẫn được khi quá sáng.
    if(!quiet && !overload) return d;
    d.red=target(red_,red,contact && stable && (!hasTracked_ || now-lastTracked_>=15000),overload);
    d.ir=target(ir_,ir,contact && stable && (!hasTracked_ || now-lastTracked_>=15000),overload);
    d.changed=d.red!=red_ || d.ir!=ir_;
    return d;
  }
  void commit(uint64_t now,uint8_t red,uint8_t ir) {
    red_=red;ir_=ir;lastChange_=now;resetWindow();++changes_;
  }
  uint8_t red()const{return red_;} uint8_t ir()const{return ir_;}
  uint32_t changes()const{return changes_;}
 private:
  static uint8_t target(uint8_t current,uint32_t dc,bool contact,bool overload) {
    if(overload || dc>180000) return uint8_t(std::max(16,int(current)-10));
    if(contact && dc<20000) return uint8_t(std::min(100,int(current)+10));
    return current;
  }
  uint8_t red_=50,ir_=50;uint64_t lastTracked_=0,lastChange_=0,redSum_=0,irSum_=0,stableRedSum_=0,stableIrSum_=0;
  uint32_t count_=0,stableCount_=0,changes_=0;bool overload_=false,hasTracked_=false;
};
}

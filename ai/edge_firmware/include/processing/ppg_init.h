#pragma once
#include <cstddef>
#include <cstdint>

namespace asd {
// Một giao dịch mỗi poll; thời gian chờ reset trải qua nhiều vòng sensing.
class PpgInitializer {
 public:
  enum class Step : uint8_t { Idle, Probe, ResetWrite, ResetWait, Configure, Verify, ClearStatus, Ready, Failed };
  enum class Failure : uint8_t { None, Transport, PartId, ResetTimeout, Configuration };
  void start(uint32_t now, uint8_t led, bool wristDense=false,uint8_t ir=0) {
    step_=Step::Probe; failure_=Failure::None; index_=0; started_=now; led_=led;irLed_=ir?ir:led;
    faultReg_=0xff; expected_=observed_=0;
    fifoConfig_=wristDense ? 0x7f : 0x5f;
    sampleConfig_=wristDense ? 0x2f : 0x2b;
  }
  bool running() const { return step_!=Step::Idle && step_!=Step::Ready && step_!=Step::Failed; }
  Step step() const { return step_; }
  Failure failure() const { return failure_; }
  uint8_t faultReg() const { return faultReg_; }
  uint8_t expected() const { return expected_; }
  uint8_t observed() const { return observed_; }
  template<class Transport> Step poll(Transport& bus, uint32_t now) {
    uint8_t value=0;
    switch(step_) {
      case Step::Probe:
        if (!bus.read(0xff,&value,1)) return fail(Failure::Transport,0xff);
        if (value!=0x15) return fail(Failure::PartId,0xff,0x15,value);
        step_=Step::ResetWrite; break;
      case Step::ResetWrite:
        if (!bus.write(0x09,0x40)) return fail(Failure::Transport,0x09);
        started_=now; step_=Step::ResetWait; break;
      case Step::ResetWait:
        if (!bus.read(0x09,&value,1)) return fail(Failure::Transport,0x09);
        if (!(value&0x40)) { step_=Step::Configure; index_=0; }
        else if (uint32_t(now-started_)>=100) return fail(Failure::ResetTimeout,0x09,0,value&0x40);
        break;
      case Step::Configure: {
        // RED+IR, 200/avg4 hoặc 400/avg8: cùng FIFO50Hz. Bật mode sau cùng.
        constexpr uint8_t regs[]={0x02,0x03,0x08,0x0a,0x0c,0x0d,0x04,0x05,0x06,0x09};
        const uint8_t values[]={0,0,fifoConfig_,sampleConfig_,led_,irLed_,0,0,0,0x03};
        if (!bus.write(regs[index_],values[index_])) return fail(Failure::Transport,regs[index_]);
        if (++index_==sizeof(regs)) step_=Step::Verify;
        break;
      }
      case Step::Verify: {
        uint8_t data[6]{};
        if (!bus.read(0x08,data,6)) return fail(Failure::Transport,0x08);
        constexpr uint8_t indices[]={0,1,2,4,5},masks[]={0xff,0x07,0x7f,0xff,0xff};
        const uint8_t expected[]={fifoConfig_,0x03,sampleConfig_,led_,irLed_};
        for (size_t i=0;i<5;++i) if ((data[indices[i]]&masks[i])!=expected[i])
          return fail(Failure::Configuration,uint8_t(0x08+indices[i]),expected[i],data[indices[i]]&masks[i]);
        step_=Step::ClearStatus; break;
      }
      case Step::ClearStatus:
        if (!bus.read(0x00,&value,1)) return fail(Failure::Transport,0x00);
        step_=Step::Ready; break;
      default: break;
    }
    return step_;
  }
 private:
  Step fail(Failure why,uint8_t reg,uint8_t expected=0,uint8_t observed=0) {
    failure_=why; faultReg_=reg; expected_=expected; observed_=observed;
    step_=Step::Failed; return step_;
  }
  Step step_=Step::Idle;
  Failure failure_=Failure::None;
  uint32_t started_=0;
  uint8_t index_=0,led_=0x1f,irLed_=0x1f,faultReg_=0xff,expected_=0,observed_=0;
  uint8_t fifoConfig_=0x5f,sampleConfig_=0x2b;
};
} // namespace asd

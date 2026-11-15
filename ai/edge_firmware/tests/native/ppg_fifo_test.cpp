#include "processing/ppg_fifo.h"

#include <array>
#include <cstdlib>
#include <iostream>
#include <vector>

namespace {
void require(bool value, const char* message) {
  if (!value) { std::cerr << message << '\n'; std::exit(1); }
}

struct FakeTransport {
  uint8_t start = 0;
  uint8_t pending = 0;
  uint8_t overflow = 0;
  uint8_t before = 0;
  uint8_t after = 0;
  size_t statusReads = 0;
  size_t fifoReads = 0;
  size_t position = 0;
  int failedRegister = -1;
  size_t failedBurst = 0;
  std::vector<asd::PpgSample> source;

  explicit FakeTransport(uint8_t count = 0, uint8_t readPointer = 0)
      : start(readPointer), pending(count) {
    for (uint32_t i = 0; i < count; ++i) source.push_back({12300 + i, 100500 + i});
  }

  bool read(uint8_t reg, uint8_t* out, size_t length) {
    if (reg == failedRegister) return false;
    if (reg == 0) {
      require(length == 1, "bad status read size");
      *out = statusReads++ == 0 ? before : after;
      return true;
    }
    if (reg >= 4 && reg <= 6) {
      require(length == 1, "metadata burst would repeat the first pointer on some modules");
      *out = reg == 4 ? (start + pending) % 32 : (reg == 5 ? overflow : start);
      return true;
    }
    require(reg == 7 && length <= 30 && length % 6 == 0, "bad FIFO transaction");
    if (++fifoReads == failedBurst) return false;
    for (size_t i = 0; i < length / 6; ++i) {
      require(position < source.size(), "read past snapshot");
      const auto sample = source[position++];
      for (size_t channel = 0; channel < 2; ++channel) {
        const uint32_t value = channel == 0 ? sample.red : sample.ir;
        out[i * 6 + channel * 3] = (value >> 16) & 0xff;
        out[i * 6 + channel * 3 + 1] = (value >> 8) & 0xff;
        out[i * 6 + channel * 3 + 2] = value & 0xff;
      }
    }
    return true;
  }
};
}  // namespace

int main() {
  size_t cases = 0;
  for (bool after : {false,true}) {
    FakeTransport bus(2); if(after)bus.after=0x20;else bus.before=0x20;
    asd::PpgSample samples[32]; const auto r=asd::readPpgFifo(bus,samples);
    require(r.status==asd::PpgFifoStatus::Ok && r.count==2 && r.ambientOverflow,
            "ambient overload before/after FIFO read was lost"); ++cases;
  }
  {
    FakeTransport bus(32); bus.overflow = 31;
    asd::PpgSample samples[32];
    const auto fault = asd::readPpgFifo(bus, samples);
    uint32_t discarded = 0;
    require(asd::discardPpgFifo(bus, fault, discarded) && discarded == 32 && bus.position == 32,
            "full FIFO discard failed"); ++cases;
  }
  {
    FakeTransport bus(8); bus.overflow = 1; bus.failedBurst = 2;
    asd::PpgSample samples[32];
    const auto fault = asd::readPpgFifo(bus, samples);
    uint32_t discarded = 0;
    require(!asd::discardPpgFifo(bus, fault, discarded) && discarded == 5,
            "partial discard failure not reported"); ++cases;
  }
  // Bao gồm đúng 4 và bội số 4: đường SparkFun cũ có thể trả available=0.
  for (uint8_t count : {0, 1, 4, 5, 8, 16, 17, 31}) {
    for (uint8_t readPointer : {0, 29}) {
      FakeTransport bus(count, readPointer);
      asd::PpgSample samples[32];
      const auto result = asd::readPpgFifo(bus, samples);
      require(result.status == asd::PpgFifoStatus::Ok && result.count == count,
              "batch lost or rejected");
      require(bus.position == count, "wrong consumed count");
      for (size_t i = 0; i < count; ++i) {
        require(samples[i].red == 12300 + i && samples[i].ir == 100500 + i,
                "sample order/channel/value mismatch");
      }
      ++cases;
    }
  }
  {
    FakeTransport bus(2); bus.source[0] = {0xffffff, 0xfedcba};
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.count == 2 && samples[0].red == 0x3ffff && samples[0].ir == (0xfedcba & 0x3ffff),
            "18-bit decode mismatch"); ++cases;
  }
  for (uint8_t lost : {1, 31}) {
    FakeTransport bus(31); bus.overflow = lost;
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.status == asd::PpgFifoStatus::Overflow && r.count == 0 &&
            r.overflowLowerBound == lost && bus.fifoReads == 0,
            "overflow not checked before pop"); ++cases;
  }
  {
    FakeTransport bus; bus.before = 0x80;
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.status == asd::PpgFifoStatus::AmbiguousFull && r.count == 0,
            "full FIFO treated as empty"); ++cases;
  }
  {
    FakeTransport bus(17); bus.before = 0x80;
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.status == asd::PpgFifoStatus::Ok && r.count == 17 && r.almostFull,
            "valid backlog rejected"); ++cases;
  }
  for (int reg : {0, 4, 5, 6, 7}) {
    FakeTransport bus(8); bus.failedRegister = reg;
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.status == asd::PpgFifoStatus::IoError && r.count == 0,
            "I2C failure accepted"); ++cases;
  }
  {
    FakeTransport bus(8); bus.failedBurst = 2;
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.status == asd::PpgFifoStatus::IoError && r.count == 0 && bus.position == 5,
            "partially read batch exposed as valid"); ++cases;
  }
  for (uint8_t interrupt : {0x80, 0x01}) {
    FakeTransport bus(8); bus.after = interrupt;
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.count == 0 && r.status != asd::PpgFifoStatus::Ok,
            "gap/reset during burst accepted"); ++cases;
  }
  {
    FakeTransport bus(2); bus.before = 0x01;
    asd::PpgSample samples[32]; const auto r = asd::readPpgFifo(bus, samples);
    require(r.status == asd::PpgFifoStatus::PowerReset && bus.fifoReads == 0,
            "sensor reset not detected"); ++cases;
  }
  std::cout << "PASS: " << cases << " PPG FIFO cases (software only)\n";
}

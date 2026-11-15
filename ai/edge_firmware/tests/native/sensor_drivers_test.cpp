#include "MAX30102Sensor.h"
#include "MPU6050Sensor.h"
#include "GSRSensor.h"
#include "communication/telemetry_serializer.h"
#include "Wire.h"
#include "processing/ppg_wrist.h"
#include "processing/ppg_wrist_motion.h"
#include <cstdlib>
#include <iostream>
#include <limits>

namespace {
unsigned cases = 0;
unsigned observedSamples = 0;
uint64_t observedLastTime = 0;
void check(bool ok, const char* why) {
  if (!ok) { std::cerr << "FAIL: " << why << '\n'; std::exit(1); }
}
void observe(uint64_t measured, uint32_t red, uint32_t ir) {
  check(measured > observedLastTime && red > 0 && ir > 0, "trace sample order/value");
  observedLastTime = measured; ++observedSamples;
}
void reset() { fakeNowMs = 1000; Wire = TwoWire(); Wire1 = TwoWire(true); }
void validateSnapshot(const MAX30102Data& ppg = {}, const MPU6050Data& imu = {}, const GSRData& gsr = {}) {
  const auto s = captureTelemetrySnapshot(ppg, imu, gsr, millis(), fakeNowMs);
  std::cout << asd::telemetryJson(s, fakeNowMs, fakeNowMs, "SYN-SENSORS", "SYNTHETIC", ASD_FIRMWARE_VERSION, "") << '\n';
}
void finishInitialization(MAX30102Sensor& sensor) {
  for (unsigned i=0;i<30 && sensor.isInitializing();++i) {
    fakeNowMs+=10; const unsigned before=Wire.transactions;
    (void)sensor.read();
    check(Wire.transactions-before<=1,"PPG initialization used more than one transaction per tick");
  }
  check(!sensor.isInitializing(),"PPG initialization did not terminate");
}
Availability configure(MAX30102Sensor& sensor) {
  (void)sensor.begin(); finishInitialization(sensor);
  return sensor.isReady() ? Availability::READY :
      (sensor.getStatus()==PPGStatus::DISCONNECTED ? Availability::UNAVAILABLE : Availability::ERROR);
}
void configure(MPU6050Sensor& sensor) {
  (void)sensor.begin();
  const auto before = fakeNowMs;
  (void)sensor.read();
  check(fakeNowMs == before, "initialization blocked sensing clock");
  fakeNowMs += 100; (void)sensor.read();
  fakeNowMs += 30; (void)sensor.read();
}
MAX30102Data feed(MAX30102Sensor& sensor, float bpm, uint32_t milliseconds,
                 uint32_t batchSize = 1, float* phaseValue = nullptr,
                 float dc = 100000, float amplitude = 1800) {
  float phase = phaseValue ? *phaseValue : 0;
  MAX30102Data reading{};
  const float step = 2 * 3.14159265358979323846f * bpm / 60 / 50;
  for (uint32_t i = 0; i < milliseconds / 20; ++i) {
    fakeNowMs += 20; phase += step;
    if (phase > 2 * 3.14159265358979323846f) phase -= 2 * 3.14159265358979323846f;
    const float ac = std::sin(phase) * amplitude;
    Wire.pushPpg(static_cast<uint32_t>(dc*.8f + ac*.7f), static_cast<uint32_t>(dc + ac));
    if ((i+1) % batchSize == 0) reading = sensor.read();
  }
  if (phaseValue) *phaseValue = phase;
  return reading;
}
}

int main() {
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    (void)feed(sensor, 80, 10000);
    check(sensor.signalQuality(fakeNowMs).score > .99f, "PPG sample coverage not recorded");
    for (unsigned i = 0; i < 100; ++i) (void)sensor.read();
    check(sensor.signalQuality(fakeNowMs + 1001).score < 0, "PPG cache renewed quality");
    ++cases;
  }
  {
    reset(); MPU6050Sensor sensor; configure(sensor);
    for (unsigned i = 0; i < 500; ++i) {
      fakeNowMs += 20;
      Wire1.pushImu(0, 0, -16384, i % 2 ? 0 : 32767, 0, 0);
      (void)sensor.read();
    }
    check(sensor.accelerationQuality(fakeNowMs).score > .99f &&
          std::fabs(sensor.rotationQuality(fakeNowMs).score - .5f) < .01f,
          "gyro saturation contaminated acceleration quality or got hidden by EMA");
    ++cases;
  }
  {
    reset(); GSRSensor sensor; (void)sensor.begin();
    for (unsigned i = 0; i < 200; ++i) {
      fakeNowMs += 50; fakeRawAdc = i % 2 ? 1800 : 0; (void)sensor.read();
    }
    check(std::fabs(sensor.signalQuality(fakeNowMs).score - .5f) < .01f,
          "GSR low rail missing from quality");
    fakeRawAdc = 1800;
    ++cases;
  }
  for (uint32_t actualUs : {19950u,20050u,20100u}) {
    asd::SampleClock fixed,tracked(true);
    unsigned legacyGaps=0; uint64_t last=0;
    for (uint64_t i=1;i<=6000;++i) {
      const uint64_t captured=1000+i*actualUs/1000;
      legacyGaps+=fixed.batch(captured,1,20).gap;
      const auto r=tracked.batch(captured,1,20);
      check(!r.gap && r.first<=captured && r.first>last,
            "slow oscillator drift created a false gap or future timestamp");
      last=r.first;
    }
    if (actualUs>20000)check(legacyGaps>0,"clock regression must reproduce the old false gap");
    ++cases;
  }
  {
    asd::SampleClock tracked(true);uint64_t last=0;
    for (uint64_t i=1;i<=2000;++i) {
      const uint64_t captured=1000+i*4*20050/1000+i%3;
      const auto r=tracked.batch(captured,4,20);
      check(!r.gap && r.first>last && r.first+60<=captured,
            "FIFO batch drift tracking reordered samples or invented future times");
      last=r.first+60;
    }
    const auto gap=tracked.batch(last+400,1,20);
    check(gap.gap && gap.first==last+400,"large genuine clock gap was hidden"); ++cases;
  }
  {
    asd::SampleClock tracked(true);
    check(tracked.batch(50,5,20).gap,"impossible FIFO timestamp accepted"); ++cases;
  }
  {
    asd::SampleClock tracked(true);(void)tracked.batch(1000,1,20);
    check(tracked.batch(1070,1,20).gap,
          "drift tracking hid a real acquisition pause with too few FIFO samples"); ++cases;
  }
  for (uint8_t reg : {uint8_t(0x08),uint8_t(0x0a)}) {
    reset(); MAX30102Sensor sensor;
    const bool dense=PPG_RAW_SAMPLE_RATE_HZ==400;
    Wire.readValueRegister=reg;
    Wire.readValue=reg==0x08 ? (dense ? 0x5f : 0x7f) : (dense ? 0x2b : 0x2f);
    (void)configure(sensor);
    check(!sensor.isReady() && sensor.acquisitionStats().lastFault.phase==PpgFaultPhase::ConfigCheck &&
          sensor.acquisitionStats().lastFault.reg==reg,
          "readback from the other acquisition profile must not be accepted"); ++cases;
  }
  {
    asd::WristMotionGuard guard;
    check(guard.update(1000,1000,true,true,true,0) && !guard.allowsHr(),"motion guard needs a clean window"); ++cases;
    for(uint64_t t=1020;t<=11000;t+=20)guard.update(t,t,true,true,true,0);
    check(guard.allowsHr(),"quiet wrist did not open"); ++cases;
    check(guard.update(11020,11020,true,true,true,.4f) && !guard.allowsHr(),"motion kept cached HR"); ++cases;
    check(guard.update(11040,11040,true,true,true,0) && !guard.allowsHr(),"motion stop must restart HR history"); ++cases;
    for(uint64_t t=11060;t<=21040;t+=20)guard.update(t,t,true,true,true,0);
    check(guard.allowsHr(),"quiet recovery failed"); ++cases;
    check(guard.update(21060,20000,true,true,true,0) && !guard.allowsHr(),"stale IMU accepted"); ++cases;
    guard.update(21080,21080,true,false,true,0);check(!guard.allowsHr(),"uncalibrated IMU accepted"); ++cases;
    guard.update(21100,21100,true,true,true,NAN);check(!guard.allowsHr(),"NaN movement accepted"); ++cases;
    guard.update(21120,21140,true,true,true,0);check(!guard.allowsHr(),"future IMU accepted"); ++cases;
    guard.update(21140,21140,true,true,true,0);
    check(guard.update(1000,1000,true,true,true,0) && !guard.allowsHr(),"clock rollback retained clean window"); ++cases;
    check(guard.update(3000,3000,true,true,true,0) && !guard.allowsHr(),"loop gap retained clean window"); ++cases;
  }
  {
    using Level=asd::WristOpticalLevel;
    check(asd::assessWrist(0,0,false,false,false,false,false).level==Level::NoReturn,"dark wrist level");
    check(asd::assessWrist(90000,0,false,true,false,false,false).level==Level::Settling,"settling wrist level");
    check(asd::assessWrist(90000,0,false,true,true,false,false).level==Level::Warming,"warming wrist level");
    check(asd::assessWrist(90000,5,true,true,true,false,false).level==Level::Weak,"weak wrist level");
    check(asd::assessWrist(90000,300,true,true,true,false,false).level==Level::Unresolved,"large AC is not confirmed HR");
    check(asd::assessWrist(90000,300,true,true,true,false,true).level==Level::Measuring,"accepted wrist level");
    check(asd::assessWrist(90000,300,true,true,true,true,true).level==Level::Overload,"overload wins over old HR");
    cases+=7;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    (void)feed(sensor,80,15000);
    Wire.registers[0x00]=0x20; fakeNowMs+=20; Wire.pushPpg(80000,100000);
    const auto r=sensor.read();
    check(!r.valid && !r.hasHeartRateTimestamp && r.opticalOverload && sensor.isReady() &&
          sensor.acquisitionStats().ambientOverflowEvents==1 && sensor.acquisitionStats().ioErrors==0,
          "ambient saturation must invalidate HR without an I2C reconnect"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor;
    check(sensor.begin()==Availability::UNAVAILABLE && sensor.isInitializing() && !sensor.isReady(),
          "async startup must not claim READY before configuration");
    const auto before=fakeNowMs; const auto r=sensor.read();
    check(fakeNowMs==before && !r.valid && !r.hasSampleTimestamp,
          "reset write blocked or exposed a fabricated sample");
    finishInitialization(sensor); check(sensor.isReady(),"async startup failed"); ++cases;
  }
  {
    reset(); Wire.ppgResetStuck=true; MAX30102Sensor sensor;
    (void)configure(sensor); const auto& stats=sensor.acquisitionStats();
    check(!sensor.isReady() && stats.initFailures==1 && stats.lastInitDurationMs<=120 &&
          stats.lastFault.kind==PpgFaultKind::ResetTimeout && stats.lastFault.reg==0x09,
          "stuck reset must expire across ticks, with exact fault"); ++cases;
  }
  {
    reset(); Wire.registers[0xff]=0x33; MAX30102Sensor sensor;
    (void)configure(sensor); const auto& f=sensor.acquisitionStats().lastFault;
    check(!sensor.isReady() && f.reg==0xff && f.expected==0x15 && f.observed==0x33,
          "part ID mismatch evidence missing"); ++cases;
  }
  {
    reset(); Wire.failedWriteRegister=0x0c; Wire.failureDelayMs=50;
    MAX30102Sensor sensor; (void)configure(sensor); const auto& stats=sensor.acquisitionStats();
    check(stats.initFailures==1 && stats.maxInitStepUs==50000 && Wire.registers[0x0d]==0 &&
          stats.lastFault.phase==PpgFaultPhase::InitWrite && stats.lastFault.reg==0x0c,
          "failed write must stop setup immediately, not accumulate timeouts"); ++cases;
  }
  {
    reset(); Wire.shortReadRegister=0x08; Wire.shortReadLimit=3;
    MAX30102Sensor sensor; (void)configure(sensor); const auto& f=sensor.acquisitionStats().lastFault;
    check(!sensor.isReady() && f.phase==PpgFaultPhase::ConfigRead && f.requested==6 && f.received==3,
          "short config read was silently accepted"); ++cases;
  }
  {
    reset(); Wire.failPpgProbe=true; Wire.failureDelayMs=50; MAX30102Sensor sensor;
    (void)configure(sensor); const auto attempts=sensor.acquisitionStats().initAttempts;
    const auto before=fakeNowMs;
    for (unsigned i=0;i<100;++i) (void)sensor.read();
    check(fakeNowMs==before && sensor.acquisitionStats().initAttempts==attempts &&
          sensor.acquisitionStats().maxInitStepUs==50000,
          "disconnected probe must honor backoff without repeated blocking"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor); sensor.setSampleObserver(observe);
    (void)feed(sensor, 100, 320, 4);
    check(observedSamples == 16, "trace lost samples before processing");
    sensor.setSampleObserver(nullptr); (void)feed(sensor, 100, 320, 4);
    check(observedSamples == 16, "trace disable ignored"); ++cases;
  }
  for (float bpm : {40.f, 60.f, 100.f, 150.f, 180.f, 200.f}) {
    reset(); MAX30102Sensor sensor;
    check(configure(sensor) == Availability::READY, "PPG setup");
    const bool dense=PPG_RAW_SAMPLE_RATE_HZ==400;
    check(Wire.registers[0x08] == (dense ? 0x7f : 0x5f) &&
          Wire.registers[0x0a] == (dense ? 0x2f : 0x2b) &&
          PPG_EFFECTIVE_RATE_HZ==50 && PPG_SAMPLE_PERIOD_MS==20,
          "PPG validated register profile must preserve FIFO50Hz");
    const auto reading = feed(sensor, bpm, 45000);
    if (!reading.valid || std::fabs(reading.heartRate - bpm) > 4) {
      std::cerr << "PPG synthetic bpm=" << bpm << " actual=" << reading.heartRate << '\n';
      check(false, "PPG rate/declared range mismatch");
    }
    check(sensor.acquisitionStats().samples == 2250, "PPG count"); ++cases;
    validateSnapshot(reading);
  }
  for (uint32_t batch : {4u, 8u, 16u}) {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    const auto reading = feed(sensor, 100, 44800, batch);
    check(reading.valid && std::fabs(reading.heartRate - 100) < 4,
          "delayed FIFO batch changed HR");
    check(sensor.acquisitionStats().samples == 2240, "lost software-ring samples"); ++cases;
  }
  for (float dc : {30000.f, 50000.f}) {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    const auto reading = feed(sensor, 100, 15000, 1, nullptr, dc, 1500);
    check(reading.valid && reading.contactSettled && std::fabs(reading.heartRate - 100) < 4,
          "wrist contact below/crossing old50k threshold flickered"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    (void)feed(sensor, 100, 15000);
    MAX30102Data reading;
    for (unsigned i = 0; i < 8; ++i) {
      fakeNowMs += 20; Wire.pushPpg(800, 1000); reading = sensor.read();
      check(!reading.valid, "HR held through absent contact");
    }
    check(!reading.fingerDetected && !reading.hasHeartRateTimestamp, "contact loss failed to invalidate HR"); ++cases;
    const auto restored = feed(sensor, 100, 15000, 1, nullptr, 30000);
    check(restored.valid, "HR failed to reacquire lower-intensity wrist contact"); ++cases;
  }
  {
    asd::PpgContact gate(10000,6000,1000);
    for (unsigned i = 0; i < 60; ++i) gate.update(30000, 1000+i*20);
    const auto jump = gate.update(100000,2200);
    check(jump.present && !jump.restart && jump.settled && jump.usable,
          "one DC step erased the rolling window instead of leaving pulse validation to the tracker"); ++cases;
  }
  {
    reset(); Wire.emulateNoRolloverStall = true;
    MAX30102Sensor sensor; (void)configure(sensor);
    const auto reading = feed(sensor, 100, 15000);
    check(reading.valid && sensor.acquisitionStats().samples == 750 &&
          sensor.acquisitionStats().overflowEvents == 0,
          "observed no-rollover stall returned"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    float phase = 0;
    (void)feed(sensor, 60, 30000, 1, &phase);
    const auto isolated = feed(sensor, 120, 1000, 1, &phase);
    check(isolated.heartRate < 80, "isolated extra peaks doubled HR"); ++cases;
    const auto recovered = feed(sensor, 60, 15000, 1, &phase);
    check(recovered.valid && std::fabs(recovered.heartRate - 60) < 5,
          "isolated faster pulse corrupted stable RR"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    float phase = 0;
    (void)feed(sensor, 60, 30000, 1, &phase);
    const auto reading = feed(sensor, 120, 12000, 1, &phase);
    check(reading.valid && std::fabs(reading.heartRate - 120) < 5,
          "HR step still locked to old RR/slow EMA"); ++cases;
    validateSnapshot(reading);
    Wire.pushPpg(0x3ffff, 0x3ffff); fakeNowMs += 20;
    check(!sensor.read().valid && sensor.acquisitionStats().clippedSamples == 1,
          "PPG clipping accepted"); ++cases;
    (void)feed(sensor, 60, 12000);
    Wire.pushPpg(80000, 100000); Wire.registers[0x05] = 31;
    check(!sensor.read().valid && sensor.acquisitionStats().overflowEvents == 1,
          "PPG overflow kept old HR"); ++cases;
    check(sensor.isReady() && Wire.registers[0x05] == 0 &&
          sensor.acquisitionStats().discardedSamples == 1,
          "overflow recovery loop failed to pop/clear counter"); ++cases;
    const auto recovered = feed(sensor, 100, 15000);
    check(recovered.valid, "PPG failed to recover after discarding broken batch"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    (void)feed(sensor, 60, 15000);
    const auto measured = sensor.read();
    fakeNowMs += 10;
    const auto cached = sensor.read();
    check(cached.newSamples == 0 && cached.heartRateMonotonicMs == measured.heartRateMonotonicMs,
          "cache refreshed window estimate timestamp"); ++cases;
    MAX30102Data flat;
    for (unsigned i = 0; i < 300; ++i) {
      fakeNowMs += 20; Wire.pushPpg(80000,100000); flat = sensor.read();
    }
    check(flat.fingerDetected && flat.contactSettled && !flat.valid && !flat.hasHeartRateTimestamp &&
          !captureTelemetrySnapshot(flat,{}, {},millis(),fakeNowMs).heartRateValid,
          "rejected window still valid in driver/telemetry"); ++cases;
    validateSnapshot(flat);
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    (void)feed(sensor, 60, 15000);
    fakeNowMs += 3100;
    const auto reading = sensor.read();
    check(!reading.valid && !reading.hasHeartRateTimestamp, "stopped PPG retained HR"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    for (unsigned i = 0; i < 500; ++i) {
      fakeNowMs += 20; Wire.pushPpg(1000, 1500);
      check(!sensor.read().valid, "no skin accepted as pulse");
    }
    ++cases;
  }
  {
    reset(); fakeNowMs = uint64_t(UINT32_MAX) - 6000;
    MAX30102Sensor sensor; (void)configure(sensor);
    const auto reading = feed(sensor, 100, 15000);
    check(reading.valid && std::fabs(reading.heartRate - 100) < 4, "PPG millis wrap"); ++cases;
  }
  {
    reset(); MPU6050Sensor sensor; configure(sensor);
    check(sensor.isReady(), "MPU configure readback");
    check(Wire1.registers[0x19] == 19 && Wire1.registers[0x1a] == 5 &&
          Wire1.registers[0x23] == 0xf8, "MPU FIFO/rate/filter config"); ++cases;
    MPU6050Data reading;
    for (unsigned i = 0; i < 110; ++i) {
      fakeNowMs += 20; Wire1.pushImu(); reading = sensor.read();
    }
    check(reading.valid && reading.gyroCalibrated && std::fabs(reading.rawGx_deg - 1) < .01 &&
          std::fabs(reading.gx_deg) < .01 && std::fabs(reading.gy_deg) < .01 &&
          std::fabs(reading.az - 9.80665) < .001, "IMU bias/sign/units/raw preservation"); ++cases;
    validateSnapshot({}, reading);
    const auto cached = sensor.read();
    check(cached.newSamples == 0 && cached.sampleMonotonicMs == reading.sampleMonotonicMs,
          "IMU cache counted as sample"); ++cases;
    fakeNowMs += 80;
    for (unsigned i = 0; i < 4; ++i) Wire1.pushImu(0,0,-16384,1310,0,0);
    reading = sensor.read();
    check(reading.valid && reading.newSamples == 4 && std::fabs(reading.gx_deg - 9) < .01,
          "IMU backlog/bias must remain frozen during motion"); ++cases;
    fakeNowMs += 20; Wire1.pushImu(32767);
    check(!sensor.read().valid && sensor.acquisitionStats().clipped == 1, "IMU clipping accepted"); ++cases;
    Wire1.registers[0x3a] = 0x10;
    check(!sensor.read().valid && !sensor.isReady(), "IMU overflow accepted"); ++cases;
  }
  {
    reset(); MPU6050Sensor sensor; configure(sensor);
    fakeNowMs += 501;
    check(!sensor.read().valid && !sensor.isReady(), "IMU reset/stalled FIFO never recovered"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; Wire.failedRegister = 0x08;
    check(configure(sensor) == Availability::ERROR, "PPG failed config write accepted"); ++cases;
    const auto& s = sensor.acquisitionStats();
    check(s.initAttempts == 1 && s.initFailures == 1 && s.initSuccesses == 0 &&
          s.lastFault.phase == PpgFaultPhase::InitWrite && s.lastFault.reg == 0x08 &&
          s.lastFault.kind == PpgFaultKind::Transmit && s.lastFault.code == 4 &&
          s.lastFault.requested == 1 && s.lastFault.received == 0,
          "configuration I2C failure lost phase/register/byte/code evidence"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; Wire.failPpgProbe = true;
    check(configure(sensor) == Availability::UNAVAILABLE &&
          sensor.acquisitionStats().lastFault.kind == PpgFaultKind::Transmit &&
          sensor.acquisitionStats().lastFault.reg == 0xff &&
          sensor.acquisitionStats().lastFault.code == 4,
          "direct probe must preserve the actual register and Wire error"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; Wire.readValueRegister = 0x0a; Wire.readValue = 0x27;
    check(configure(sensor) == Availability::ERROR, "bad sampling register accepted");
    const auto& f = sensor.acquisitionStats().lastFault;
    check(f.phase == PpgFaultPhase::ConfigCheck && f.kind == PpgFaultKind::Mismatch &&
          f.reg == 0x0a && f.expected == (PPG_RAW_SAMPLE_RATE_HZ==400 ? 0x2f : 0x2b) && f.observed == 0x27,
          "readback mismatch did not identify expected/observed register"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    fakeNowMs += 20; Wire.pushPpg(80000,100000);
    Wire.shortReadRegister = 0x07; Wire.shortReadLimit = 3;
    const auto r = sensor.read(); const auto& f = sensor.acquisitionStats().lastFault;
    check(!r.valid && !r.hasSampleTimestamp && !sensor.isReady() &&
          f.phase == PpgFaultPhase::Acquire && f.kind == PpgFaultKind::ShortRead &&
          f.reg == 0x07 && f.requested == 6 && f.received == 3,
          "partial FIFO frame not invalidated or missing-byte evidence lost"); ++cases;
  }
  {
    reset(); MAX30102Sensor sensor; (void)configure(sensor);
    (void)feed(sensor,80,15000);
    Wire.failedRegister = 0x00;
    check(!sensor.read().valid && !sensor.isReady(), "I2C fault retained HR");
    const uint64_t failedAt = fakeNowMs;
    check(sensor.acquisitionStats().lastFault.phase == PpgFaultPhase::Acquire &&
          sensor.acquisitionStats().lastFault.reg == 0x00,
          "initial acquisition fault not recorded"); ++cases;
    fakeNowMs += 2999; (void)sensor.read();
    check(sensor.acquisitionStats().initAttempts == 1, "recovery retried before existing 3s delay");
    Wire.failedRegister = 0x08; ++fakeNowMs; (void)sensor.read(); finishInitialization(sensor);
    check(sensor.acquisitionStats().initAttempts == 2 && sensor.acquisitionStats().initFailures == 1 &&
          sensor.acquisitionStats().lastFault.phase == PpgFaultPhase::InitWrite,
          "second failed initialization not distinguished from initial read fault"); ++cases;
    Wire.failedRegister = -1; fakeNowMs += 3000; (void)sensor.read(); finishInitialization(sensor);
    check(sensor.isReady() && sensor.acquisitionStats().initAttempts == 3 &&
          sensor.acquisitionStats().initSuccesses == 2,
          "recovery attempt counters incorrect");
    fakeNowMs += 20; Wire.pushPpg(80000,100000);
    const auto fresh = sensor.read();
    check(fresh.newSamples == 1 && !fresh.valid && !fresh.hasHeartRateTimestamp &&
          sensor.acquisitionStats().lastRecoveryDurationMs == fakeNowMs-failedAt &&
          sensor.acquisitionStats().lastRecoveryDurationMs >= 6020 &&
          sensor.acquisitionStats().lastRecoveryDurationMs < 6500 &&
          sensor.acquisitionStats().recoveryCause.reg == 0x00 &&
          sensor.acquisitionStats().recoveryCause.phase == PpgFaultPhase::Acquire &&
          sensor.acquisitionStats().lastFault.phase == PpgFaultPhase::InitWrite,
          "6s recovery timeline incorrect, old HR leaked or fault evidence erased"); ++cases;
  }
  for (int mode : {0,1,2}) {
    reset(); MPU6050Sensor sensor;
    if (mode == 0) Wire1.registers[0x75] = 0x98;
    if (mode == 1) Wire1.corruptRegister = 0x19;
    if (mode == 2) Wire1.failedRegister = 0x1a;
    configure(sensor);
    check(!sensor.isReady() && !sensor.read().valid, "MPU ID/config failure accepted"); ++cases;
  }
  {
    reset(); Wire1.registers[0x75] = 0x74;
    MPU6050Sensor sensor; configure(sensor);
    check(sensor.isReady() && Wire1.registers[0x1d] == 0x45, "MPU6515 profile rejected or accel filter missing");
    MPU6050Data reading;
    for (unsigned i = 0; i < 110; ++i) {
      fakeNowMs += 20; Wire1.pushImu(); reading = sensor.read();
    }
    check(reading.valid && reading.whoAmI == 0x74 && std::isnan(reading.temperature),
          "MPU6515 sample rejected or wrong temperature conversion"); ++cases;
    validateSnapshot({}, reading);
  }
  {
    reset(); MPU6050Sensor sensor; configure(sensor);
    for (unsigned i = 0; i < 200; ++i) {
      fakeNowMs += 20; Wire1.pushImu(0,0,-16384,3930,0,0);
      check(!sensor.read().valid, "calibrated while clearly moving");
    }
    fakeNowMs += 200;
    for (unsigned i = 0; i < 9; ++i) Wire1.pushImu();
    check(!sensor.read().valid && sensor.acquisitionStats().gaps > 0,
          "unbounded IMU backlog accepted"); ++cases;
  }
  {
    reset(); fakeCalibration = ESP_ADC_CAL_VAL_EFUSE_TP_FIT; fakeRawAdc = 1800;
    GSRSensor sensor; check(sensor.begin() == Availability::READY, "GSR begin");
    auto reading = sensor.read();
    check(reading.rawADC == 1800 && reading.rawVoltage_mV == 1800 && reading.voltageCalibrated,
          "GSR used uncalibrated 3300/4095 scaling"); ++cases;
    for (unsigned i = 0; i < 140; ++i) { fakeNowMs += 50; reading = sensor.read(); }
    check(reading.valid && !reading.conductanceCalibrated && std::isnan(reading.conductance_uS),
          "unverified GSR mapping emitted uS");
    const auto snapshot = captureTelemetrySnapshot({}, {}, reading, millis(), fakeNowMs);
    check(snapshot.gsrReadable && !snapshot.gsrValid, "GSR raw lost or unverified delta enabled"); ++cases;
    validateSnapshot({}, {}, reading);
    fakeRawAdc = 4095; fakeNowMs += 50; reading = sensor.read();
    check(reading.status == GSRStatus::SATURATED && !reading.valid, "GSR ADC rail accepted"); ++cases;
    fakeRawAdc = 1800; fakeNowMs += 50;
    check(sensor.read().status == GSRStatus::CALIBRATING, "GSR reused baseline after rail"); ++cases;
  }
  {
    reset(); fakeCalibration = ESP_ADC_CAL_VAL_DEFAULT_VREF; fakeRawAdc = 1800;
    GSRSensor sensor; (void)sensor.begin(); const auto reading = sensor.read();
    const auto snapshot = captureTelemetrySnapshot({}, {}, reading, millis(), fakeNowMs);
    check(snapshot.gsrReadable && !snapshot.gsrValid && std::isnan(reading.voltage),
          "GSR default Vref masqueraded as calibrated voltage"); ++cases;
    validateSnapshot({}, {}, reading);
    fakeCalibration = ESP_ADC_CAL_VAL_EFUSE_TP_FIT;
  }
  {
    uint32_t scheduled = UINT32_MAX - 5;
    check(!asd::sampleDue(UINT32_MAX, scheduled, 10) && asd::sampleDue(7, scheduled, 10),
          "scheduler wrap");
    scheduled = 0;
    check(asd::sampleDue(57, scheduled, 20) && scheduled == 40 &&
          !asd::sampleDue(59, scheduled, 20), "scheduler drift/catchup duplication"); ++cases;
    asd::VoltageBaseline baseline;
    for (unsigned i = 0; i < 150; ++i)
      baseline.update(1000 + 50*i, i%2 ? 1000 : 2000);
    check(!baseline.ready(), "unstable GSR baseline accepted"); ++cases;
    check(std::isnan(asd::gsrConductance(1, false, 3.3f, .1f, 25000)) &&
          std::isfinite(asd::gsrConductance(1, true, 3.3f, .1f, 25000)) &&
          std::isnan(asd::gsrConductance(.1f, true, 3.3f, .1f, 25000)), "GSR mapping bounds"); ++cases;
    asd::SampleClock clock;
    auto t = clock.batch(uint64_t(UINT32_MAX) - 5, 4, 20);
    check(!t.gap && t.first + 60 == uint64_t(UINT32_MAX) - 5, "clock first batch");
    t = clock.batch(uint64_t(UINT32_MAX) + 78, 4, 20);
    check(!t.gap && t.first + 60 <= uint64_t(UINT32_MAX) + 78, "clock wrap/jitter/future");
    t = clock.batch(uint64_t(UINT32_MAX) + 1000, 1, 20);
    check(t.gap, "sample clock lost gap"); ++cases;
    asd::GyroBias bias;
    for (unsigned i = 0; i < 130; ++i)
      bias.update(1000 + i*20, {{0,0,9.80665f}}, {{float(i%2 ? -2 : 2), 0, 0}});
    check(!bias.ready(), "gyro unstable low-speed window accepted"); ++cases;
  }
  std::cout << "PASS: " << cases << " production sensor driver cases (fake I2C/ADC/clock; no hardware)\n";
}

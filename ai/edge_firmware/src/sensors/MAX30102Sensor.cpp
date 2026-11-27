#include "MAX30102Sensor.h"
#include <esp_timer.h>

#include <Wire.h>
#include <algorithm>   // std::sort
#include "processing/ppg_fifo.h"

namespace {
void recordFault(PpgAcquisitionStats& stats, PpgFaultPhase phase, PpgFaultKind kind,
                 uint8_t reg = 0xff, size_t requested = 0, size_t received = 0,
                 uint8_t code = 0) {
  ++stats.faultEvents;
  stats.lastFault = {};
  stats.lastFault.atMs = millis(); stats.lastFault.phase = phase; stats.lastFault.kind = kind;
  stats.lastFault.reg = reg; stats.lastFault.requested = requested;
  stats.lastFault.received = received; stats.lastFault.code = code;
}
struct PpgWireTransport {
  PpgAcquisitionStats& stats;
  PpgFaultPhase phase;
  bool write(uint8_t reg, uint8_t value) {
    Wire.beginTransmission(I2C_ADDR_MAX30102);
    Wire.write(reg); Wire.write(value);
    const uint8_t code=Wire.endTransmission();
    if (code==0) return true;
    recordFault(stats,phase,PpgFaultKind::Transmit,reg,1,0,code);
    return false;
  }
  bool read(uint8_t reg, uint8_t* bytes, size_t length) {
    Wire.beginTransmission(I2C_ADDR_MAX30102);
    Wire.write(reg);
    const uint8_t code = Wire.endTransmission(false);
    if (code != 0) {
      recordFault(stats, phase, PpgFaultKind::Transmit, reg, length, 0, code);
      return false;
    }
    const size_t received = Wire.requestFrom(I2C_ADDR_MAX30102, length);
    if (received != length) {
      recordFault(stats, phase, PpgFaultKind::ShortRead, reg, length, received);
      while (Wire.available()) (void)Wire.read();
      return false;
    }
    for (size_t i = 0; i < length; ++i) {
      if (!Wire.available()) {
        recordFault(stats, phase, PpgFaultKind::Drain, reg, length, i);
        return false;
      }
      bytes[i] = static_cast<uint8_t>(Wire.read());
    }
    return true;
  }
};
}  // namespace

// =============================================================================
Availability MAX30102Sensor::begin() {
  static_assert(((PPG_SAMPLE_RATE_HZ==200 && PPG_SAMPLE_AVERAGE==4) ||
                 (PPG_SAMPLE_RATE_HZ==400 && PPG_SAMPLE_AVERAGE==8)) && PPG_LED_MODE==2 &&
                PPG_PULSE_WIDTH==411 && PPG_ADC_RANGE==4096,
                "Revalidate PpgInitializer register profile for new acquisition settings");
  ready_=false; status_=PPGStatus::PULSE_ACQUIRING;
  resetCalculations(); contact_.reset(); clock_.reset();
  hasSampleTime_=hasPollTime_=false;
  ++acquisitionStats_.initAttempts;
  acquisitionStats_.lastInitStartedMs=millis();
  lastRetryMs_=millis();
  exposureStep_=0;
  if(!exposureStarted_){exposure_.begin(millis(),PPG_LED_BRIGHTNESS,PPG_LED_BRIGHTNESS);exposureStarted_=true;}
  exposure_.resetWindow();
  initializer_.start(millis(),exposure_.red(),PPG_SAMPLE_RATE_HZ==400,exposure_.ir());
  return advanceInitialization();
}

Availability MAX30102Sensor::advanceInitialization() {
  using Init=asd::PpgInitializer;
  const auto previous=initializer_.step();
  PpgFaultPhase phase=PpgFaultPhase::InitWrite;
  if (previous==Init::Step::Probe) phase=PpgFaultPhase::Probe;
  else if (previous==Init::Step::ResetWait) phase=PpgFaultPhase::ResetWait;
  else if (previous==Init::Step::Verify || previous==Init::Step::ClearStatus) phase=PpgFaultPhase::ConfigRead;
  PpgWireTransport bus{acquisitionStats_,phase};
  const auto started=esp_timer_get_time();
  const auto state=initializer_.poll(bus,millis());
  acquisitionStats_.maxInitStepUs=std::max(acquisitionStats_.maxInitStepUs,
      static_cast<uint32_t>(esp_timer_get_time()-started));
  if (state!=Init::Step::Ready && state!=Init::Step::Failed) return Availability::UNAVAILABLE;
  const uint32_t elapsed=uint32_t(millis()-acquisitionStats_.lastInitStartedMs);
  acquisitionStats_.lastInitDurationMs=elapsed;
  acquisitionStats_.maxInitDurationMs=std::max(acquisitionStats_.maxInitDurationMs,elapsed);
  if (state==Init::Step::Failed) {
    const auto failure=initializer_.failure();
    if (failure!=Init::Failure::Transport) {
      recordFault(acquisitionStats_,failure==Init::Failure::Configuration ? PpgFaultPhase::ConfigCheck : phase,
          failure==Init::Failure::ResetTimeout ? PpgFaultKind::ResetTimeout : PpgFaultKind::Mismatch,
          initializer_.faultReg());
      acquisitionStats_.lastFault.expected=initializer_.expected();
      acquisitionStats_.lastFault.observed=initializer_.observed();
    }
    ++acquisitionStats_.initFailures;
    markRecovery(); lastRetryMs_=millis();
    status_=previous==Init::Step::Probe ? PPGStatus::DISCONNECTED : PPGStatus::ERROR;
    return status_==PPGStatus::DISCONNECTED ? Availability::UNAVAILABLE : Availability::ERROR;
  }
  ++acquisitionStats_.initSuccesses;
  configuredMs_=millis(); ready_=true; status_=PPGStatus::NO_FINGER;
  Serial.printf("[MAX30102] READY FIFO=%uHz redLED=%u irLED=%u FW=%s\n",
      PPG_EFFECTIVE_RATE_HZ,exposure_.red(),exposure_.ir(),ASD_FIRMWARE_VERSION);
  return Availability::READY;
}

void MAX30102Sensor::markRecovery() {
  if (!recovering_) {
    recovering_ = true; recoveryStartedMs_ = millis();
    acquisitionStats_.recoveryCause = acquisitionStats_.lastFault;
  }
}

void MAX30102Sensor::resetCalculations() {
  ++analysisGeneration_; lastCountedQualityMs_=0;
  rate_.reset(); beatTracker_.reset(); acceptedWindows_ = 0;
  hasValidHeartRateTime_ = false;
  lastValidHeartRateMs_ = 0; heartRateMonotonicMs_ = 0;
  latestHeartRateBpm_=0;latestBeatIntervalMs_=0;latestBeatPeakToPeak_=0.0f;latestHeartRateSource_=0;
}

void MAX30102Sensor::processRate(uint32_t ir, uint32_t red, uint64_t measured) {
  static_assert(PPG_EFFECTIVE_RATE_HZ == 50 && HR_MIN_PHYSIOLOGICAL == 40 &&
                HR_MAX_PHYSIOLOGICAL == 200 && asd::PpgBeatTracker::kMinimumBpm == HR_MIN_PHYSIOLOGICAL &&
                asd::PpgBeatTracker::kMaximumBpm == HR_MAX_PHYSIOLOGICAL,
                "Update PPG window/filter/range with acquisition profile");
  const auto started = esp_timer_get_time();
  const auto motion=motionHistory_.nearest(measured);
  const auto estimate = rate_.update(ir, red, measured, &motion);
  acquisitionStats_.maxRateProcessingUs = std::max(acquisitionStats_.maxRateProcessingUs,
      static_cast<uint32_t>(esp_timer_get_time() - started));
  if (!estimate.updated) return;
  (void)asd::ppgHybridSubmit(rate_,estimate.measuredAt,analysisGeneration_);

}

MAX30102Data MAX30102Sensor::read() {
  MAX30102Data data{};
  data.redLed=exposure_.red();data.irLed=exposure_.ir();data.exposureChanges=exposure_.changes();
  data.exposureSettling=exposureStep_!=0;


  // Tự động kết nối lại định kỳ không nghẽn bus nếu cảm biến bị ngắt
  if (!ready_) {
    if (initializer_.running()) {
      (void)advanceInitialization();
      data.status=status_;
      return data;
    }
    const unsigned long now = millis();
    if (now - lastRetryMs_ >= I2C_RETRY_INTERVAL_MS) {
      lastRetryMs_ = now;
      if (begin() == Availability::READY) {
        Serial.println(F("[MAX30102] >>> Phục hồi kết nối thành công! <<<"));
      }
    }
    data.status = status_;
    return data;
  }

  // 1. Không dùng check()/available(): ring nội bộ SparkFun chỉ có 4 phần tử.
  if(exposureStep_){
    (void)serviceExposure();
    data.status=PPGStatus::PULSE_ACQUIRING;data.exposureSettling=true;
    return data;
  }
  const uint32_t pollMs = millis();
  if (hasPollTime_) {
    acquisitionStats_.maxPollGapMs = std::max(acquisitionStats_.maxPollGapMs,
                                             uint32_t(pollMs - lastPollMs_));
  }
  lastPollMs_ = pollMs;
  hasPollTime_ = true;
  asd::PpgSample samples[32];
  PpgWireTransport transport{acquisitionStats_, PpgFaultPhase::Acquire};
  const auto batch = asd::readPpgFifo(transport, samples);
  acquisitionStats_.writePointer = batch.writePointer;
  acquisitionStats_.readPointer = batch.readPointer;
  acquisitionStats_.overflowCounter = batch.overflowLowerBound;
  acquisitionStats_.interrupt = batch.interrupt;
  if (batch.status != asd::PpgFifoStatus::Ok) {
    ++acquisitionStats_.gapEvents;
    if (batch.status == asd::PpgFifoStatus::IoError) ++acquisitionStats_.ioErrors;
    if (batch.status == asd::PpgFifoStatus::Overflow ||
        batch.status == asd::PpgFifoStatus::AmbiguousFull) {
      ++acquisitionStats_.overflowEvents;
      acquisitionStats_.overflowSamplesLowerBound += batch.overflowLowerBound;
      uint32_t discarded = 0;
      transport.phase = PpgFaultPhase::Discard;
      const bool recovered = asd::discardPpgFifo(transport, batch, discarded);
      acquisitionStats_.discardedSamples += discarded;
      if (recovered) {
        // Không công nhận lô lỗi; tiếp tục đọc các mẫu mới sau gap thay vì
        // soft-reset làm lặp lại counter khởi động trước khi pop lần đầu.
        resetCalculations(); contact_.reset(); clock_.reset(); hasSampleTime_ = false;
        configuredMs_ = millis();
        status_ = PPGStatus::PULSE_ACQUIRING; data.status = status_;
        return data;
      }
      ++acquisitionStats_.ioErrors;
    }
    // Không nối nhịp qua khoảng mất; re-init xóa nửa mẫu/cấu hình sau lỗi nguồn.
    if (batch.status == asd::PpgFifoStatus::PowerReset)
      recordFault(acquisitionStats_, PpgFaultPhase::Acquire, PpgFaultKind::PowerReset, 0x00);
    markRecovery();
    resetCalculations();
    clock_.reset();
    contact_.reset();
    hasSampleTime_ = false;
    ready_ = false;
    lastRetryMs_ = millis();
    status_ = PPGStatus::ERROR;
    data.status = status_;
    return data;
  }
  const size_t sampleCount = batch.count;
  const bool hasNewData = sampleCount != 0;
  acquisitionStats_.samples += static_cast<uint32_t>(sampleCount);
  acquisitionStats_.maxBatch = std::max(acquisitionStats_.maxBatch,
                                       static_cast<uint32_t>(sampleCount));
  bool clipped = false;
  for (size_t i = 0; i < sampleCount; ++i) {
    if (samples[i].red == 0x3ffff || samples[i].ir == 0x3ffff) {
      ++acquisitionStats_.clippedSamples;
      clipped = true;
    }
  }
  if (hasNewData) {
    latestIr_ = samples[sampleCount - 1].ir;
    latestRed_ = samples[sampleCount - 1].red;
  }

  const uint64_t captured = static_cast<uint64_t>(esp_timer_get_time()) / 1000;
  if ((!hasNewData && uint32_t(millis() - (hasSampleTime_ ? lastSampleMs_ : configuredMs_)) > 500) ||
      (hasNewData && captured < (sampleCount - 1) * PPG_SAMPLE_PERIOD_MS)) {
    recordFault(acquisitionStats_, PpgFaultPhase::Watchdog, PpgFaultKind::NoSamples);
    markRecovery();
    ++acquisitionStats_.gapEvents;
    resetCalculations(); contact_.reset(); clock_.reset(); ready_ = false; hasSampleTime_ = false;
    lastRetryMs_ = millis(); status_ = PPGStatus::ERROR; data.status = status_;
    return data;
  }
  asd::SampleBatchTime timing{};
  if (hasNewData) {
    if (recovering_) {
      acquisitionStats_.lastRecoveryDurationMs = uint32_t(millis() - recoveryStartedMs_);
      recovering_ = false;
    }
    timing = clock_.batch(captured, static_cast<uint32_t>(sampleCount), PPG_SAMPLE_PERIOD_MS);
    if (timing.gap) { ++acquisitionStats_.gapEvents; contact_.reset(); resetCalculations(); }
    sampleMonotonicMs_ = timing.first + (sampleCount - 1) * PPG_SAMPLE_PERIOD_MS;
    lastSampleMs_ = static_cast<uint32_t>(sampleMonotonicMs_); hasSampleTime_ = true;
  }
  data.sampleMonotonicMs = sampleMonotonicMs_;
  data.sampleUpdatedAtMs = lastSampleMs_;
  data.hasSampleTimestamp = hasSampleTime_;
  data.newSamples = sampleCount;
  if (observer_) {
    for (size_t i = 0; i < sampleCount; ++i)
      observer_(timing.first + i * PPG_SAMPLE_PERIOD_MS, samples[i].red, samples[i].ir);
  }

  data.irValue        = latestIr_;
  data.redValue       = latestRed_;

  for(size_t i=0;i<sampleCount;++i)exposure_.observe(samples[i].red,samples[i].ir,
      batch.ambientOverflow || samples[i].red==0x3ffff || samples[i].ir==0x3ffff,
      contact_.settled() && exposureQuiet_ && samples[i].ir>=PPG_IR_CONTACT_OFF &&
      samples[i].red!=0x3ffff && samples[i].ir!=0x3ffff);
  data.redLed=exposure_.red();data.irLed=exposure_.ir();data.exposureChanges=exposure_.changes();
  data.exposureSettling=captured<exposureSettledAt_;
  for (size_t i = 0; i < sampleCount; ++i)
    quality_.add(timing.first + i * PPG_SAMPLE_PERIOD_MS, batch.ambientOverflow ||
        samples[i].red == 0x3ffff || samples[i].ir == 0x3ffff);
  data.opticalOverload=clipped || batch.ambientOverflow;
  if (batch.ambientOverflow) ++acquisitionStats_.ambientOverflowEvents;
  const auto exposureDecision=exposureEnabled_?exposure_.decide(captured,contact_.settled(),exposureQuiet_):asd::PpgExposure::Decision{};
  if(exposureDecision.changed){
    targetRed_=exposureDecision.red;targetIr_=exposureDecision.ir;exposureStep_=1;
    resetCalculations();data.exposureSettling=true;data.status=PPGStatus::PULSE_ACQUIRING;return data;
  }
  if (data.opticalOverload) {
    resetCalculations();
    contact_.reset();
    status_ = PPGStatus::ERROR;
    data.status = status_;
    return data;
  }

  // Tiếp xúc hysteresis/debounce; một mẫu yếu không xóa cả cửa sổ.
  if (hasNewData) {
    for (size_t i = 0; i < sampleCount; ++i) {
      const uint64_t measured = timing.first + i * PPG_SAMPLE_PERIOD_MS;
      const auto contact = contact_.update(samples[i].ir, measured);
      if (contact.restart) { ++acquisitionStats_.contactRestarts; resetCalculations(); }
      if (contact.usable && measured>=exposureSettledAt_) {
        processRate(samples[i].ir, samples[i].red, measured);
        (void)beatTracker_.update(samples[i].ir, measured);
      }
    }
  }
  // Cửa sổ dài tiếp tục chạy để lấy bằng chứng chất lượng; HR gửi đi được
  // chọn riêng từ bộ dò RR bên dưới.
  data.fingerDetected = contact_.present();
  data.contactSettled = contact_.settled();
  const auto& estimate = rate_.estimate();
  data.hasRateWindow=estimate.measuredAt!=0;
  data.acceptedWindows = acceptedWindows_;
  data.periodicity = estimate.periodicity;
  data.recentPeriodicity = estimate.recentPeriodicity;
  data.redPeriodicity = estimate.redPeriodicity;
  data.redRecentPeriodicity = estimate.redRecentPeriodicity;
  data.bandPowerRatio = estimate.bandPowerRatio;
  data.pulseAmplitude = estimate.amplitude;
  data.heartRate = 0;

  // Chỉ đọc metadata chẩn đoán, không đổi cổng nhận hoặc số HR.
  asd::PpgHybridResult signalAnalysis{};
  const bool hasAnalysis=asd::ppgHybridLatest(signalAnalysis);
  if (hasAnalysis) {
    const auto& a = signalAnalysis.analysis;
    data.qualityAnalysisFresh = a.measuredAt != 0 && a.generation == analysisGeneration_ &&
        captured >= a.measuredAt && captured - a.measuredAt <= 1500;
    data.qualityEvidence = a.sqi;
    data.irEvidence=a.irEvidence;data.redEvidence=a.redEvidence;
    data.motionCoverage=a.motionCoverage;data.motionOverlap=a.motionOverlap;
    data.motionSupported=data.qualityAnalysisFresh && a.valid && a.motionSupported;
    data.motionCorrected=a.motionCorrected;
  }
  // HR lấy từ bộ dò RR đã dùng trong firmware cũ. Bộ theo cửa sổ hiện tại
  // vẫn chạy để cung cấp bằng chứng chất lượng, nhưng không thay thế HR đã chọn.
  const auto& beatEstimate=beatTracker_.estimate();
  const bool recentBeatRate = beatEstimate.valid && beatEstimate.measuredAtMs != 0 &&
      captured >= beatEstimate.measuredAtMs && captured-beatEstimate.measuredAtMs <= 3000;
  if (recentBeatRate && data.fingerDetected && data.contactSettled) {
    latestHeartRateBpm_=beatEstimate.bpm;
    latestBeatIntervalMs_=beatEstimate.intervalMs;
    latestBeatPeakToPeak_=beatEstimate.peakToPeak;
    latestHeartRateSource_=8;
    heartRateMonotonicMs_=beatEstimate.measuredAtMs;
    lastValidHeartRateMs_=static_cast<uint32_t>(heartRateMonotonicMs_);
    if (lastCountedQualityMs_ != heartRateMonotonicMs_) {
      ++acceptedWindows_;
      lastCountedQualityMs_=heartRateMonotonicMs_;
    }
  }
  const bool recentSelectedRate=latestHeartRateBpm_ >= HR_MIN_PHYSIOLOGICAL &&
      latestHeartRateBpm_ <= HR_MAX_PHYSIOLOGICAL && latestHeartRateSource_ != 0 &&
      heartRateMonotonicMs_ != 0 && captured >= heartRateMonotonicMs_ &&
      captured-heartRateMonotonicMs_ <= 3000 && data.fingerDetected;
  hasValidHeartRateTime_=recentSelectedRate;
  if (recentSelectedRate) {
    data.heartRate=latestHeartRateBpm_;
    data.beatIntervalMs=latestBeatIntervalMs_;
    data.beatPeakToPeak=latestBeatPeakToPeak_;
    data.heartRateSource=latestHeartRateSource_;
    exposure_.tracked(heartRateMonotonicMs_);
  } else {
    data.heartRate=0;
    data.beatIntervalMs=0;
    data.beatPeakToPeak=0.0f;
    data.heartRateSource=0;
  }
#if !defined(ASD_PPG_NATIVE_HYBRID_TEST)
  // Chuẩn hóa chất lượng tín hiệu HR đồng bộ với bộ dò nhịp PpgBeatTracker đã chốt
  if (data.fingerDetected && data.contactSettled && beatEstimate.quality > 0.0f) {
    data.qualityAnalysisFresh = true;
    data.qualityEvidence = recentSelectedRate
        ? std::max(data.qualityEvidence, beatEstimate.quality)
        : std::min(0.45f, std::max(data.qualityEvidence, beatEstimate.quality));
  }
#endif
  const bool chosenValid=recentSelectedRate;
  data.acceptedWindows=acceptedWindows_;

  // 4. Xác định trạng thái ổn định tín hiệu
  if (!data.fingerDetected) {
    status_ = PPGStatus::NO_FINGER;
    data.valid = false;
  } else if (!data.contactSettled || !hasValidHeartRateTime_ || !chosenValid || data.heartRate < HR_MIN_PHYSIOLOGICAL) {
    status_    = PPGStatus::PULSE_ACQUIRING;
    data.valid = false;
  } else {
    status_    = PPGStatus::VALID;
    data.valid = true;
  }

  data.status = status_;
  data.heartRateUpdatedAtMs = lastValidHeartRateMs_;
  data.heartRateMonotonicMs = heartRateMonotonicMs_;
  data.hasHeartRateTimestamp = hasValidHeartRateTime_;
  return data;
}


// Một giao dịch I2C mỗi poll; shutdown, kiểm tra LED, xóa FIFO rồi mở lại.
bool MAX30102Sensor::serviceExposure() {
  PpgWireTransport bus{acquisitionStats_,PpgFaultPhase::ConfigRead};
  uint8_t value=0;bool ok=true;const auto faultsBefore=acquisitionStats_.faultEvents;
  const uint8_t step=exposureStep_;
  switch(exposureStep_){
    case 1:ok=bus.write(0x09,0x83);break; // Shutdown: không sinh mẫu khi sửa FIFO.
    case 2:ok=bus.write(0x0c,targetRed_);break;
    case 3:ok=bus.read(0x0c,&value,1) && value==targetRed_;break;
    case 4:ok=bus.write(0x0d,targetIr_);break;
    case 5:ok=bus.read(0x0d,&value,1) && value==targetIr_;break;
    case 6:ok=bus.write(0x04,0);break;
    case 7:ok=bus.write(0x05,0);break;
    case 8:ok=bus.write(0x06,0);break;
    case 9:ok=bus.write(0x09,0x03);break;
    default:return false;
  }
  if(!ok){
    if(acquisitionStats_.faultEvents==faultsBefore){
      recordFault(acquisitionStats_,PpgFaultPhase::ConfigCheck,PpgFaultKind::Mismatch,step==3?0x0c:0x0d);
      acquisitionStats_.lastFault.expected=step==3?targetRed_:targetIr_;
      acquisitionStats_.lastFault.observed=value;
    }
    markRecovery();ready_=false;exposureStep_=0;lastRetryMs_=millis();
    resetCalculations();contact_.reset();clock_.reset();hasSampleTime_=false;return false;
  }
  if(++exposureStep_>9){
    const uint64_t now=static_cast<uint64_t>(esp_timer_get_time())/1000;
    exposure_.commit(now,targetRed_,targetIr_);quality_.reset();exposureStep_=0;
    exposureSettledAt_=now+1000;configuredMs_=millis();
    resetCalculations();clock_.reset();hasSampleTime_=hasPollTime_=false;
    // Bỏ quá độ1s sau đổi dòng, không coi là lần tháo thiết bị.
    return true;
  }
  return false;
}

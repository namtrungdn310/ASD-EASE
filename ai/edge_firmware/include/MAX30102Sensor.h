#pragma once
#include "board_config.h"
#include "processing/measurement_quality.h"
#include "processing/ppg_rate.h"
#include "processing/sensor_math.h"
#include "processing/ppg_contact.h"
#include "processing/ppg_hybrid_worker.h"
#include "processing/ppg_init.h"
#include "processing/ppg_exposure.h"
#include "processing/ppg_beat_tracker.h"

// =============================================================================
// MAX30102 — PPG và ước tính nhịp tim theo cửa sổ
// =============================================================================

struct MAX30102Data {
  uint64_t sampleMonotonicMs = 0, heartRateMonotonicMs = 0;
  uint32_t sampleUpdatedAtMs = 0, heartRateUpdatedAtMs = 0;
  uint32_t newSamples = 0;
  bool hasSampleTimestamp = false, hasHeartRateTimestamp = false;
  bool contactSettled = false;
  bool qualityAnalysisFresh = false;
  float qualityEvidence = 0;
  float irEvidence=0,redEvidence=0,motionCoverage=0,motionOverlap=0;
  bool motionSupported=false,motionCorrected=false;
  uint8_t redLed=50,irLed=50;
  uint32_t exposureChanges=0;
  bool exposureSettling=false;
  bool hasRateWindow = false, opticalOverload = false;
  bool wristMotionAllowed = false;
  uint8_t wristMotionReason = 0;
  uint32_t acceptedWindows = 0;
  float periodicity = 0, recentPeriodicity = 0, redPeriodicity = 0;
  float redRecentPeriodicity = 0, bandPowerRatio = 0;
  uint8_t heartRateSource = 0; // 8 bộ dò RR từ firmware cũ; chỉ dùng trong log chẩn đoán.
  uint32_t  irValue        = 0;
  uint32_t  redValue       = 0;
  float     heartRate       = 0.0f; // Tracker chu kỳ ưu tiên; RR từng nhịp là nguồn dự phòng.
  float     spO2            = NAN;                       // Không suy SpO2 từ HR hoặc kẹp về dải đẹp
  float     pulseAmplitude  = 0.0f;                      // Biên độ tương đương từ RMS, counts
  PPGStatus status          = PPGStatus::DISCONNECTED;   // Trạng thái tiếp xúc & đo đạc
  bool      fingerDetected  = false;                     // Đã đặt ngón tay hay chưa
  bool      valid           = false;                     // Cờ hợp lệ theo điều kiện nhịp tim của driver
};

enum class PpgFaultPhase : uint8_t { None, Probe, ConfigRead, ConfigCheck, Acquire, Discard, Watchdog, InitWrite, ResetWait };
enum class PpgFaultKind : uint8_t { None, Transmit, ShortRead, Drain, ProbeFailed, Mismatch, NoSamples, PowerReset, ResetTimeout };
struct PpgIoFault {
  uint32_t atMs = 0;
  PpgFaultPhase phase = PpgFaultPhase::None;
  PpgFaultKind kind = PpgFaultKind::None;
  uint8_t reg = 0xff, code = 0, expected = 0, observed = 0;
  uint16_t requested = 0, received = 0;
};
struct PpgAcquisitionStats {
  // Giữ lỗi gần nhất qua các lần phục hồi; chỉ log Serial, không đưa vào telemetry.
  PpgIoFault lastFault{};
  PpgIoFault recoveryCause{}; // Giữ nguyên lỗi mở đầu dù các lần thử sau cũng lỗi.
  uint32_t faultEvents = 0, initAttempts = 0, initSuccesses = 0, initFailures = 0;
  uint32_t lastInitStartedMs = 0, lastInitDurationMs = 0, maxInitDurationMs = 0;
  uint32_t lastRecoveryDurationMs = 0;
  uint32_t maxInitStepUs = 0;
  uint32_t samples = 0;
  uint32_t maxBatch = 0;
  uint32_t maxPollGapMs = 0;
  uint32_t ioErrors = 0;
  uint32_t overflowEvents = 0;
  uint32_t overflowSamplesLowerBound = 0;
  uint32_t gapEvents = 0;
  uint32_t clippedSamples = 0;
  uint32_t ambientOverflowEvents = 0;
  uint32_t discardedSamples = 0;
  uint32_t contactRestarts = 0;
  uint32_t maxRateProcessingUs = 0;
  uint8_t writePointer = 0, readPointer = 0, overflowCounter = 0, interrupt = 0;
};

class MAX30102Sensor {
 public:
  using SampleObserver = void (*)(uint64_t, uint32_t, uint32_t);
  void setSampleObserver(SampleObserver observer) { observer_ = observer; }
  void addMotionSample(const asd::PpgMotionSample& sample){motionHistory_.add(sample);}
  asd::PpgMotionSample motionAt(uint64_t at)const{return motionHistory_.nearest(at);}
  uint8_t redLed()const{return exposure_.red();}
  uint8_t irLed()const{return exposure_.ir();}
  uint32_t exposureGeneration()const{return exposure_.changes();}
  void setExposureQuiet(bool quiet){exposureQuiet_=quiet;exposureEnabled_=true;}
  Availability begin();
  MAX30102Data read();
  bool isReady() const { return ready_; }
  PPGStatus getStatus() const { return status_; }
  void resetCalculations();
  asd::MeasurementQuality signalQuality(uint64_t now) const { return quality_.evaluate(now, 50); }
  bool isInitializing() const { return initializer_.running(); }
  const PpgAcquisitionStats& acquisitionStats() const { return acquisitionStats_; }

 private:
  void processRate(uint32_t irValue, uint32_t redValue, uint64_t measured);
  void markRecovery();
  Availability advanceInitialization();
  bool serviceExposure();
  asd::PpgMotionHistory motionHistory_;
  asd::PpgExposure exposure_;
  bool exposureStarted_=false,exposureQuiet_=false,exposureEnabled_=false;
  uint8_t exposureStep_=0,targetRed_=50,targetIr_=50;
  uint64_t exposureSettledAt_=0;

  bool          ready_        = false;
  uint32_t lastSampleMs_ = 0, lastValidHeartRateMs_ = 0;
  uint64_t sampleMonotonicMs_ = 0, heartRateMonotonicMs_ = 0;
  bool hasSampleTime_ = false, hasValidHeartRateTime_ = false;
  PPGStatus     status_       = PPGStatus::DISCONNECTED;
  asd::PpgInitializer initializer_;
  unsigned long lastRetryMs_  = 0;
  uint32_t      latestIr_     = 0;
  uint32_t      latestRed_    = 0;
  PpgAcquisitionStats acquisitionStats_{};
  SampleObserver observer_ = nullptr;
  asd::QualityWindow quality_;
  asd::PpgBeatTracker beatTracker_;
  float latestHeartRateBpm_ = 0;
  uint8_t latestHeartRateSource_ = 0;
  uint32_t lastPollMs_ = 0;
  uint32_t configuredMs_ = 0;
  bool hasPollTime_ = false;
  bool recovering_ = false;
  uint32_t recoveryStartedMs_ = 0;

  asd::SampleClock clock_{PPG_RAW_SAMPLE_RATE_HZ==400};
  asd::PpgContact contact_{PPG_IR_FINGER_THRESHOLD, PPG_IR_CONTACT_OFF, PPG_CONTACT_SETTLE_MS};
  asd::PpgRate rate_; // Standard: bộ lọc/cửa sổ đầu vào cho tracker, không chạy profile demo.
  uint32_t acceptedWindows_ = 0;
  uint32_t analysisGeneration_ = 0;
  uint64_t lastCountedQualityMs_ = 0;
};

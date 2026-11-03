#include "communication/telemetry_serializer.h"
#include <algorithm>

static uint32_t age(uint64_t now, uint64_t measured) {
  return now >= measured ? static_cast<uint32_t>(std::min<uint64_t>(UINT32_MAX, now - measured)) : UINT32_MAX;
}

asd::ReadingSnapshot captureTelemetrySnapshot(
    const MAX30102Data& ppg, const MPU6050Data& imu, const GSRData& gsr,
    uint32_t, uint64_t monotonicNow) {
  asd::ReadingSnapshot s;
  s.capturedAtMs = monotonicNow;
  s.heartRate = ppg.heartRate;
  s.heartRateValid = ppg.valid && ppg.status == PPGStatus::VALID;
  if (ppg.hasHeartRateTimestamp) s.heartRateAgeMs = age(monotonicNow, ppg.heartRateMonotonicMs);
  if (ppg.hasSampleTimestamp) s.ppgAgeMs = age(monotonicNow, ppg.sampleMonotonicMs);
  if (gsr.hasSampleTimestamp) s.gsrAgeMs = age(monotonicNow, gsr.sampleMonotonicMs);
  if (imu.hasSampleTimestamp) s.imuAgeMs = age(monotonicNow, imu.sampleMonotonicMs);
  s.gsrAdc = gsr.rawADC;
  s.gsrDeltaPercent = gsr.percentChange;
  s.baselineConductance = gsr.baselineConductance_uS;
  s.gsrValid = gsr.valid && gsr.status == GSRStatus::VALID;
  s.gsrReadable = gsr.status == GSRStatus::VALID || gsr.status == GSRStatus::CALIBRATING;
  s.gsrCalibrating = gsr.status == GSRStatus::CALIBRATING;
  s.imuCalibrating = imu.status == IMUStatus::CALIBRATING;
  return s;
}


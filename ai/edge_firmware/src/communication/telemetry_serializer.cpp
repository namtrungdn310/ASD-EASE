#include "communication/telemetry_serializer.h"
#include <algorithm>

static uint32_t age(uint64_t now, uint64_t measured) {
  return now >= measured ? static_cast<uint32_t>(std::min<uint64_t>(UINT32_MAX, now - measured)) : UINT32_MAX;
}

asd::ReadingSnapshot captureTelemetrySnapshot(
    const MAX30102Data& ppg, const MPU6050Data& imu, const GSRData& gsr,
    uint32_t, uint64_t monotonicNow,
    asd::MeasurementQuality ppgQuality, asd::MeasurementQuality gsrQuality,
    asd::MeasurementQuality accelerationQuality, asd::MeasurementQuality rotationQuality) {
  asd::ReadingSnapshot s;
  s.capturedAtMs = monotonicNow;
  s.hasMetricQuality = true;
  s.hrQuality = asd::opticalQuality(ppgQuality, ppg.fingerDetected, ppg.contactSettled,
      ppg.wristMotionAllowed, ppg.opticalOverload, ppg.qualityAnalysisFresh, ppg.qualityEvidence);
  if(ppg.exposureSettling)s.hrQuality={-1,asd::QualityReason::WarmingUp};
  s.gsrQuality = gsrQuality;
  s.accelerationQuality = accelerationQuality;
  s.rotationQuality = rotationQuality;
  if (gsr.status == GSRStatus::SATURATED) s.gsrQuality = {0, asd::QualityReason::Saturated};
  else if (gsr.status == GSRStatus::DISCONNECTED || gsr.status == GSRStatus::ERROR)
    s.gsrQuality = {-1, asd::QualityReason::Unavailable};
  if (imu.status == IMUStatus::CALIBRATING) {
    s.accelerationQuality = s.rotationQuality = {-1, asd::QualityReason::Calibrating};
  }
  // Preserve actual acquisition counts even when optical/contact checks override the score.
  s.hrQuality.sampleCount = ppgQuality.sampleCount;
  s.gsrQuality.sampleCount = gsrQuality.sampleCount;
  s.accelerationQuality.sampleCount = accelerationQuality.sampleCount;
  s.rotationQuality.sampleCount = rotationQuality.sampleCount;

  s.heartRate = ppg.heartRate;
  // Giữ số HR mới nhất qua một sụt tiếp xúc ngắn; session protocol vẫn chặn
  // HR cũ bằng tuổi mẫu PPG và tuổi chính lần đo nhịp.
  s.heartRateValid = ppg.hasHeartRateTimestamp && ppg.fingerDetected;
  if (ppg.hasHeartRateTimestamp) s.heartRateAgeMs = age(monotonicNow, ppg.heartRateMonotonicMs);
  if (ppg.hasSampleTimestamp) s.ppgAgeMs = age(monotonicNow, ppg.sampleMonotonicMs);
  if (gsr.hasSampleTimestamp) s.gsrAgeMs = age(monotonicNow, gsr.sampleMonotonicMs);
  if (imu.hasSampleTimestamp) s.imuAgeMs = age(monotonicNow, imu.sampleMonotonicMs);
  s.gsrAdc = gsr.rawADC;
  s.gsrDeltaPercent = gsr.percentChange;
  s.baselineConductance = gsr.baselineConductance_uS;
  s.gsrValid = gsr.valid && gsr.status == GSRStatus::VALID && gsr.conductanceCalibrated;
  s.gsrReadable = gsr.status == GSRStatus::VALID || gsr.status == GSRStatus::CALIBRATING;
  s.gsrCalibrating = gsr.status == GSRStatus::CALIBRATING;
  s.imuCalibrating = imu.status == IMUStatus::CALIBRATING;
  s.movementScore = imu.movementScore;
  s.movementValid = imu.valid && imu.status == IMUStatus::VALID &&
      imu.hasSampleTimestamp && imu.movementValid;
  // Snapshot sau EMA, cùng một lần đọc và cùng hệ trục với Serial.
  s.acceleration = {{imu.ax, imu.ay, imu.az}};
  s.angularVelocity = {{imu.gx_deg, imu.gy_deg, imu.gz_deg}};
  s.imuValid = imu.valid && imu.status == IMUStatus::VALID && imu.hasSampleTimestamp;
  return s;
}


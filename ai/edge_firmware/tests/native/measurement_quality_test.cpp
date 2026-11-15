#include "communication/telemetry_serializer.h"
#include <iostream>
#include <cstdlib>

int main() {
  unsigned cases = 0;
  const auto check = [&](bool ok, const char* message) {
    if (!ok) { std::cerr << message << '\n'; std::exit(1); }
    ++cases;
  };
  const auto close = [](float a, float b) { return std::fabs(a - b) < .001f; };
  asd::QualityWindow clean, missing, clipped, gyro;
  check(clean.evaluate(9000, 50).score < 0, "empty window scored");
  for (uint64_t at = 0; at <= 9000; at += 20) {
    clean.add(at, false);
    clean.add(at, false); // Cache không phải mẫu mới.
    if (at % 40 == 0) missing.add(at, false);
    clipped.add(at, at % 40 == 0);
    gyro.add(at, at % 100 == 0);
    if (at == 1000) check(clean.evaluate(at, 50).score < 0, "warmup scored");
  }
  const auto full = clean.evaluate(9000, 50);
  check(close(full.score, 1), "clean/cached sample coverage");
  check(full.sampleCount == 400, "actual count includes cache or current bucket");
  check(missing.evaluate(9000, 50).sampleCount == 200, "missing count fabricated from rate");
  asd::QualityWindow partial;
  for (uint64_t at = 0; at < 1000; at += 20) partial.add(at, false);
  check(partial.evaluate(1000, 50).sampleCount == 50, "partial acquisition count");
  check(full.reason == asd::QualityReason::Ok, "clean reason");
  check(close(missing.evaluate(9000, 50).score, .5f), "missing sample ratio");
  check(missing.evaluate(9000, 50).reason == asd::QualityReason::MissingSamples, "missing reason");
  check(close(clipped.evaluate(9000, 50).score, .5f), "clip ratio");
  check(close(gyro.evaluate(9000, 50).score, .8f), "separate gyro saturation");
  check(clean.evaluate(10001, 50).reason == asd::QualityReason::Stale, "stale score retained");
  check(clean.evaluate(8000, 50).score < 0, "backward time scored");
  asd::QualityWindow gap;
  for (uint64_t at = 0; at < 1000; at += 20) gap.add(at, false);
  gap.add(20000, false);
  check(close(gap.evaluate(20000, 50).score, 0), "old buckets counted after gap");
  asd::QualityWindow rollover;
  const uint64_t base = (uint64_t(UINT32_MAX) / 1000) * 1000;
  for (uint64_t at = base; at <= base + 9000; at += 20) rollover.add(at, false);
  check(close(rollover.evaluate(base + 9000, 50).score, 1), "32-bit millis rollover");
  const auto optical = [&](bool contact, bool motion, bool overload, bool fresh, float evidence) {
    return asd::opticalQuality(full, contact, true, motion, overload, fresh, evidence);
  };
  check(close(optical(true, true, false, true, .8f).score, .8f), "waveform evidence omitted");
  check(close(optical(true, true, false, true, .2f).score, .2f), "weak signal raised");
  check(optical(true, true, false, true, .2f).reason == asd::QualityReason::WeakSignal, "weak reason");
  check(optical(false, true, false, true, .9f).score == 0, "no contact not zero");
  check(optical(true, false, false, true, .9f).score == 0, "motion not identified");
  check(optical(true, true, true, true, .9f).score == 0, "overload not identified");
  check(optical(true, true, false, false, .9f).score < 0, "stale analysis scored");
  check(optical(true, true, false, true, NAN).score < 0, "NaN evidence scored");

  MAX30102Data ppg{}; MPU6050Data imu{}; GSRData gsr{};
  ppg.hasSampleTimestamp = imu.hasSampleTimestamp = gsr.hasSampleTimestamp = true;
  ppg.sampleMonotonicMs = imu.sampleMonotonicMs = gsr.sampleMonotonicMs = 9000;
  ppg.fingerDetected = ppg.contactSettled = ppg.wristMotionAllowed = ppg.qualityAnalysisFresh = true;
  ppg.qualityEvidence = .8f;
  imu.valid = true; imu.status = IMUStatus::VALID; imu.az = 9.8f;
  gsr.status = GSRStatus::VALID; gsr.rawADC = 1800;
  auto snapshot = captureTelemetrySnapshot(ppg, imu, gsr, 9000, 9000,
      full, full, clipped.evaluate(9000, 50), gyro.evaluate(9000, 50));
  check(close(snapshot.hrQuality.score, .8f) && close(snapshot.accelerationQuality.score, .5f) &&
        close(snapshot.rotationQuality.score, .8f), "snapshot crossed metric quality");
  const auto emit = [&](const asd::ReadingSnapshot& s, uint64_t now) {
    const auto wire = asd::telemetryJson(s, now, now, "SYN-QUALITY", "SYNTHETIC", "quality-native-test", "");
    JsonDocument parsed;
    check(asd::parseObject(wire, parsed), "serializer failed");
    std::cout << wire << '\n';
    return parsed;
  };
  auto packet = emit(snapshot, 9000);
  check(packet["signal_quality"]["hr"]["sample_count"] == 400, "HR count missing on wire");
  check(packet["signal_quality"]["acceleration"]["sample_count"] == 400 &&
        packet["signal_quality"]["rotation"]["sample_count"] == 400, "IMU counts missing");
  check(packet["schema_version"] == "1.2" && close(packet["signal_quality"]["hr"]["score"].as<float>(), .8f),
      "version/score lost");
  packet = emit(snapshot, 10001);
  check(packet["signal_quality"]["hr"]["sample_count"].isNull(), "stale count exposed as fresh");
  check(packet["signal_quality"]["hr"]["score"].isNull() &&
        packet["signal_quality"]["rotation"]["reason"] == "stale", "cached quality not expired");
  ppg.fingerDetected = false;
  snapshot = captureTelemetrySnapshot(ppg, imu, gsr, 9000, 9000, full, full, full, full);
  packet = emit(snapshot, 9000);
  check(packet["signal_quality"]["hr"]["sample_count"] == 400, "no-contact check lost actual sample count");
  check(packet["signal_quality"]["hr"]["score"] == 0 && packet["hr_bpm"].isNull(), "absent PPG fabricated HR");
  imu.status = IMUStatus::CALIBRATING;
  snapshot = captureTelemetrySnapshot(ppg, imu, gsr, 9000, 9000, full, full, full, full);
  packet = emit(snapshot, 9000);
  check(packet["signal_quality"]["rotation"]["score"].isNull(), "gyro calibration scored");
  std::cout << "PASS: " << cases << " measurement quality cases\n";
}

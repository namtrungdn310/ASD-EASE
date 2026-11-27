#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>

#include "processing/edge_ai_inference.h"
#include "processing/hr_stability.h"
#include "processing/impact_detector.h"

namespace {

MAX30102Data makePpg(uint64_t nowMs, float hr, bool valid = true, bool finger = true,
                     uint32_t beatIntervalMs = 0, float beatPeakToPeak = 0.0f) {
  MAX30102Data d{};
  d.fingerDetected = finger;
  d.contactSettled = finger;
  d.valid = valid;
  d.heartRate = hr;
  d.beatIntervalMs = beatIntervalMs;
  d.beatPeakToPeak = beatPeakToPeak;
  d.heartRateMonotonicMs = nowMs;
  d.hasHeartRateTimestamp = valid;
  d.status = finger ? (valid ? PPGStatus::VALID : PPGStatus::PULSE_ACQUIRING) : PPGStatus::NO_FINGER;
  return d;
}

MPU6050Data makeImu(uint64_t nowMs, float ax = 0.0f, float ay = 0.0f, float az = 9.80665f,
                    float gx = 0.0f, float gy = 0.0f, float gz = 0.0f) {
  MPU6050Data d{};
  d.valid = true;
  d.hasSampleTimestamp = true;
  d.sampleMonotonicMs = nowMs;
  d.gyroCalibrated = true;
  d.ax = ax;
  d.ay = ay;
  d.az = az;
  d.gx_deg = gx;
  d.gy_deg = gy;
  d.gz_deg = gz;
  d.accelMagnitude = std::sqrt(ax * ax + ay * ay + az * az);
  d.status = IMUStatus::VALID;
  return d;
}

GSRData makeGsr(float conductanceUs, uint16_t rawAdc = 1800) {
  GSRData d{};
  d.valid = true;
  d.conductanceCalibrated = true;
  d.conductance_uS = conductanceUs;
  d.rawADC = rawAdc;
  d.status = GSRStatus::VALID;
  return d;
}

void testHrStabilityFilter() {
  asd::HrStabilityFilter filter;
  uint64_t t = 10000;

  // 1. Initial lock requires 3 consistent samples
  filter.update(t, true, true, 78.0f, t);
  assert(!filter.isFreshStable(t));
  t += 1000;
  filter.update(t, true, true, 79.0f, t);
  assert(!filter.isFreshStable(t));
  t += 1000;
  filter.update(t, true, true, 78.5f, t);
  assert(filter.isFreshStable(t));
  assert(std::fabs(filter.stableBpm() - 78.5f) < 0.1f);
  const uint64_t stableBeforeSpike = filter.lastStableAtMs();

  // 2. Sudden upward spike + slow decay back down -> hidden until steady back near baseline
  const float spikeRamp[] = {148.0f, 128.0f, 110.0f, 94.0f};
  for (float v : spikeRamp) {
    t += 1000;
    filter.update(t, true, true, v, t);
    assert(!filter.isFreshStable(t));
    // Anchor timestamp stays on last green point so UI bridges continuously <= 15s
    assert(filter.lastStableAtMs() == stableBeforeSpike);
  }
  // Settles back near 79-80 -> resumes green
  t += 1000;
  filter.update(t, true, true, 80.0f, t);
  t += 1000;
  filter.update(t, true, true, 79.5f, t);
  assert(filter.isFreshStable(t));

  // 3. Sudden downward drop + recovery -> hidden until settled
  const float dropRamp[] = {46.0f, 58.0f, 70.0f};
  for (float v : dropRamp) {
    t += 1000;
    filter.update(t, true, true, v, t);
    assert(!filter.isFreshStable(t));
  }
  t += 1000;
  filter.update(t, true, true, 78.5f, t);
  t += 1000;
  filter.update(t, true, true, 79.0f, t);
  assert(filter.isFreshStable(t));

  // 4. Smooth physiological rise (stress) -> accepted cleanly
  const float smoothRise[] = {82.0f, 85.0f, 88.0f, 91.0f, 94.0f, 97.0f};
  for (float v : smoothRise) {
    t += 1000;
    filter.update(t, true, true, v, t);
    assert(filter.isFreshStable(t));
  }
  std::cout << "[PASS] testHrStabilityFilter\n";
}

void testImpactDetector() {
  asd::ImpactDetector det;
  uint64_t t = 1000;
  // Establish calm gravity baseline @ 50Hz (20ms step)
  for (int i = 0; i < 50; ++i, t += 20) {
    det.update(t, true, 0.0f, 0.0f, 9.80665f);
  }
  assert(det.countWithin(t, 30000) == 0);

  // Single desk slap + rebound within 120ms -> counted ONLY once!
  t += 20; det.update(t, true, 0.0f, 0.0f, 22.0f);
  t += 20; det.update(t, true, 0.0f, 0.0f, 17.0f);
  t += 20; det.update(t, true, 0.0f, 0.0f, 10.0f);
  assert(det.countWithin(t, 30000) == 1);
  assert(det.inSingleImpactTransient(t));
  assert(!det.hasRepeatedImpact(t));

  // Wait past transient and trigger 2 more bangs spaced 600ms apart -> total 3 -> repeatedImpact!
  for (int k = 0; k < 2; ++k) {
    for (int i = 0; i < 30; ++i, t += 20) det.update(t, true, 0.0f, 0.0f, 9.80665f);
    t += 20; det.update(t, true, 0.0f, 0.0f, 23.0f);
    t += 20; det.update(t, true, 0.0f, 0.0f, 9.80665f);
  }
  assert(det.countWithin(t, 30000) == 3);
  assert(det.hasRepeatedImpact(t));
  assert(!det.inSingleImpactTransient(t));

  // clearHistory resets only impact count while keeping IMU gravity baseline intact
  det.clearHistory();
  assert(det.countWithin(t, 30000) == 0);
  assert(!det.hasRepeatedImpact(t));
  t += 20; det.update(t, true, 0.0f, 0.0f, 9.80665f);
  assert(det.countWithin(t, 30000) == 0);
  std::cout << "[PASS] testImpactDetector\n";
}

void testSweatyHandsAndQuietStudyingVsRealStress() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;

  // Scenario A: Sweaty palms (9.5 uS constant) + quiet studying hand + steady resting HR (76 bpm) for 65s
  for (int sec = 0; sec < 65; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      ai.update(t, makePpg(t, 76.0f), makeImu(t, 0.0f, 0.0f, 9.80665f), makeGsr(9.5f, 1400));
    }
  }
  const auto resCalm = ai.latest();
  assert(resCalm.hasProbability);
  assert(std::strcmp(resCalm.state, "NORMAL") == 0);
  assert(resCalm.probability <= 0.45f);
  assert(resCalm.edaBaselineUs > 9.0f);

  // Scenario B: Moderate stress (+12 bpm HR mean to ~88 + clear EDA phasic/tonic rise) -> ATTENTION in 70%..89%
  for (int sec = 0; sec < 65; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float wave = (step < 6) ? 1.1f : 0.0f;
      const float g = 9.5f + 0.06f * static_cast<float>(sec) + wave;
      const float hr = 85.0f + 0.12f * static_cast<float>(sec);
      ai.update(t, makePpg(t, hr), makeImu(t, 0.2f, -0.1f, 9.85f), makeGsr(g, 1180));
    }
  }
  const auto resModerate = ai.latest();
  assert(resModerate.hasProbability);
  assert(std::strcmp(resModerate.state, "ATTENTION") == 0);
  assert(resModerate.probability >= 0.70f && resModerate.probability <= 0.89f);

  // Scenario C: Extreme stress (+26 bpm HR surge to 102 + strong EDA surge + phasic peaks) -> >= 93%
  for (int sec = 0; sec < 65; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float wave = (step % 6 == 0) ? 2.4f : 0.0f;
      const float g = 11.5f + 0.12f * static_cast<float>(sec) + wave;
      const float hr = 96.0f + 0.18f * static_cast<float>(sec);
      ai.update(t, makePpg(t, hr), makeImu(t, 0.35f, -0.25f, 9.90f), makeGsr(g, 950));
    }
  }
  const auto resExtreme = ai.latest();
  assert(resExtreme.hasProbability);
  assert(std::strcmp(resExtreme.state, "ATTENTION") == 0);
  assert(resExtreme.probability >= 0.93f);
  std::cout << "[PASS] testSweatyHandsAndQuietStudyingVsRealStress (moderate="
            << resModerate.probability << ", extreme=" << resExtreme.probability << ")\n";
}

void testMildSingleChannelDoesNotTriggerAttention() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      ai.update(t, makePpg(t, 76.0f), makeImu(t, 0.0f, 0.0f, 9.80665f), makeGsr(2.0f));
    }
  }
  assert(std::strcmp(ai.latest().state, "NORMAL") == 0);

  // Only mild HR uptick (+7 bpm, < +10 bpm) while moving slightly and EDA flat -> capped <= 0.65f (NORMAL)
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float ax = (step % 2 == 0) ? 0.5f : -0.5f;
      ai.update(t, makePpg(t, 83.0f), makeImu(t, ax, 0.0f, 9.80665f), makeGsr(2.05f));
    }
  }
  assert(std::strcmp(ai.latest().state, "NORMAL") == 0);
  assert(ai.latest().probability <= 0.65f);
  std::cout << "[PASS] testMildSingleChannelDoesNotTriggerAttention (prob=" << ai.latest().probability << ")\n";
}

void testRepeatedImpactTriggersAttention() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      ai.update(t, makePpg(t, 76.0f), makeImu(t, 0.0f, 0.0f, 9.80665f), makeGsr(2.0f), false, 0);
    }
  }
  assert(std::strcmp(ai.latest().state, "NORMAL") == 0);

  // Repeated desk banging (4 impacts in 30s) + mild arousal
  for (int sec = 0; sec < 12; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float az = (step == 0 && sec % 3 == 0) ? 20.0f : 9.80665f;
      ai.update(t, makePpg(t, 82.0f), makeImu(t, 0.1f, 0.1f, az), makeGsr(2.4f), false, 4);
    }
  }
  assert(std::strcmp(ai.latest().state, "ATTENTION") == 0);
  assert(ai.latest().repeatedImpactTriggered);
  std::cout << "[PASS] testRepeatedImpactTriggersAttention\n";
}

}  // namespace

void testUncalibratedGroveGsrSeveritySpread() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;
  auto makeRawGsr = [](uint16_t rawAdc) {
    GSRData d{};
    d.valid = true;
    d.conductanceCalibrated = false;
    d.rawADC = rawAdc;
    d.status = GSRStatus::VALID;
    return d;
  };

  // Resting baseline around 1550 ADC, HR 84 bpm
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      ai.update(t, makePpg(t, 84.0f), makeImu(t, 0.0f, 0.0f, 9.80665f), makeRawGsr(1550));
    }
  }
  assert(std::strcmp(ai.latest().state, "NORMAL") == 0);

  // Moderate real-world rise like screenshot: GSR 1550 -> 2250 ADC, HR 84 -> 102 bpm
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const uint16_t adc = static_cast<uint16_t>(1550 + (sec * 700) / 62);
      const float hr = 91.0f + 0.18f * static_cast<float>(sec);
      ai.update(t, makePpg(t, hr), makeImu(t, 0.15f, 0.0f, 9.80665f), makeRawGsr(adc));
    }
  }
  const auto res = ai.latest();
  assert(std::strcmp(res.state, "ATTENTION") == 0);
  assert(res.probability >= 0.72f && res.probability <= 0.89f);
  std::cout << "[PASS] testUncalibratedGroveGsrSeveritySpread (prob=" << res.probability << ")\n";
}

void testSmoothProbabilityAndCleanAttentionExit() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;

  // 1. Calm quiet sitting -> well below 0.45 wall (around ~12%-35%, not pinned flat at 0.45)
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      ai.update(t, makePpg(t, 76.0f), makeImu(t, 0.0f, 0.0f, 9.80665f), makeGsr(2.0f));
    }
  }
  const float calmProb = ai.latest().probability;
  assert(std::strcmp(ai.latest().state, "NORMAL") == 0);
  assert(calmProb < 0.35f);

  // 2. Push into ATTENTION with multi-channel stress
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float wave = (step % 6 == 0) ? 1.5f : 0.0f;
      ai.update(t, makePpg(t, 92.0f), makeImu(t, 0.25f, -0.15f, 9.85f), makeGsr(3.2f + wave));
    }
  }
  assert(std::strcmp(ai.latest().state, "ATTENTION") == 0);
  assert(ai.latest().probability >= 0.72f);

  // 3. Recovery phase: moving hand lightly while HR falls back near baseline -> must NOT stay stuck at 0.65!
  //    It must drop smoothly below 0.55 and exit ATTENTION cleanly back to NORMAL.
  for (int sec = 0; sec < 65; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float ax = (step % 2 == 0) ? 0.35f : -0.35f;
      ai.update(t, makePpg(t, 78.0f), makeImu(t, ax, 0.1f, 9.80665f, 15.0f, 5.0f, 0.0f), makeGsr(2.05f));
    }
  }
  const auto resRecovered = ai.latest();
  assert(resRecovered.probability < 0.55f);
  assert(std::strcmp(resRecovered.state, "NORMAL") == 0);
  std::cout << "[PASS] testSmoothProbabilityAndCleanAttentionExit (calm=" << calmProb
            << ", recovered=" << resRecovered.probability << ")\n";
}

void testHrvAndGyroscopeIntelligence() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;

  // Baseline resting: HR 76, high sinusoidal HRV (~50ms RMSSD), strong PPG amp (~1200), low gyro
  for (int sec = 0; sec < 62; ++sec) {
    const uint32_t rr = (sec % 2 == 0) ? 815U : 765U;  // |diff| = 50ms -> RMSSD ~ 50ms
    for (int step = 0; step < 20; ++step) {
      t += 50;
      ai.update(t, makePpg(t, 76.0f, true, true, rr, 1200.0f),
                makeImu(t, 0.0f, 0.0f, 9.80665f, 2.0f, 1.0f, 1.0f), makeGsr(2.0f));
    }
  }
  assert(std::strcmp(ai.latest().state, "NORMAL") == 0);
  assert(ai.latest().rmssdMs > 40.0f);

  // Scenario A: Vigorous wrist movement / walking (gyro ~65 deg/s) raises HR +12 bpm cleanly,
  // HRV stays healthy (~42ms) and EDA stays steady -> stays NORMAL!
  for (int sec = 0; sec < 62; ++sec) {
    const uint32_t rr = (sec % 2 == 0) ? 700U : 658U;
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float ax = (step % 2 == 0) ? 1.5f : -1.5f;
      ai.update(t, makePpg(t, 88.0f, true, true, rr, 1180.0f),
                makeImu(t, ax, 0.8f, 9.80665f, 52.0f, 35.0f, 20.0f), makeGsr(2.10f));
    }
  }
  assert(std::strcmp(ai.latest().state, "NORMAL") == 0);
  assert(ai.latest().gyroRms >= 50.0f);

  // Scenario B: Real sympathetic stress: mild HR uptick (+8 bpm to 84), but HRV plunges (~14ms RMSSD),
  // vasoconstriction cuts PPG amplitude (1200 -> 650), and EDA shows phasic arousal -> confirms ATTENTION!
  for (int sec = 0; sec < 62; ++sec) {
    const uint32_t rr = (sec % 2 == 0) ? 721U : 707U;  // RMSSD ~ 14ms
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float wave = (step % 5 == 0) ? 0.55f : 0.0f;
      ai.update(t, makePpg(t, 84.0f, true, true, rr, 650.0f),
                makeImu(t, 0.1f, 0.0f, 9.80665f, 5.0f, 3.0f, 2.0f), makeGsr(2.45f + wave));
    }
  }
  const auto resHrv = ai.latest();
  assert(resHrv.rmssdMs > 0.0f && resHrv.rmssdMs < 20.0f);
  assert(resHrv.vasoRatio < 0.70f);
  assert(std::strcmp(resHrv.state, "ATTENTION") == 0);
  std::cout << "[PASS] testHrvAndGyroscopeIntelligence (hrv=" << resHrv.rmssdMs
            << "ms, vaso=" << resHrv.vasoRatio << ", prob=" << resHrv.probability << ")\n";
}

void testInPlaceResetRestoresCleanCalibrationWithoutStackTemporary() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;

  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      ai.update(t, makePpg(t, 92.0f, true, true, 650U, 700.0f),
                makeImu(t, 0.25f, -0.15f, 9.85f, 12.0f, 4.0f, 3.0f), makeGsr(3.5f, 1200), false, 3);
    }
  }
  assert(ai.latest().hasProbability);
  assert(ai.latest().windowSeconds == 60);

  ai.reset();
  assert(!ai.latest().hasProbability);
  assert(ai.latest().windowSeconds == 0);
  assert(ai.latest().impacts30s == 0);
  assert(std::strcmp(ai.latest().state, "UNCERTAIN") == 0);

  t += 1000;
  const auto afterOne = ai.update(t, makePpg(t, 76.0f), makeImu(t), makeGsr(2.0f), false, 0);
  assert(!afterOne.hasProbability);
  assert(afterOne.windowSeconds == 1);
  assert(std::strcmp(afterOne.state, "CALIBRATING") == 0);
  std::cout << "[PASS] testInPlaceResetRestoresCleanCalibrationWithoutStackTemporary\n";
}

void testNoFalseNormalOrCalibratingBeforeWristContact() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;

  // 1. At boot, never worn (even if exposureSettling momentarily true) -> must stay UNCERTAIN immediately!
  for (int sec = 0; sec < 8; ++sec) {
    t += 1000;
    auto noWear = makePpg(t, 0.0f, false, false);
    noWear.exposureSettling = (sec < 2);
    const auto res = ai.update(t, noWear, makeImu(t), makeGsr(2.0f));
    assert(std::strcmp(res.state, "UNCERTAIN") == 0);
    assert(res.windowSeconds == 0);
  }

  // 2. Grazing touch (fingerDetected=true, contactSettled=false, no HR) -> stays UNCERTAIN!
  t += 1000;
  auto graze = makePpg(t, 0.0f, false, true);
  graze.contactSettled = false;
  const auto resGraze = ai.update(t, graze, makeImu(t), makeGsr(2.0f));
  assert(std::strcmp(resGraze.state, "UNCERTAIN") == 0);
  assert(resGraze.windowSeconds == 0);

  // 3. Real settled contact -> starts CALIBRATING cleanly
  t += 1000;
  const auto resWear = ai.update(t, makePpg(t, 76.0f, true, true), makeImu(t), makeGsr(2.0f));
  assert(std::strcmp(resWear.state, "CALIBRATING") == 0);
  assert(resWear.windowSeconds == 1);
  std::cout << "[PASS] testNoFalseNormalOrCalibratingBeforeWristContact\n";
}

void testFiveSecondGracePreservesStateAndProbabilityThenResetsCleanly() {
  asd::EdgeAiInference ai;
  uint64_t t = 1000;

  // Reach active ATTENTION state
  for (int sec = 0; sec < 62; ++sec) {
    for (int step = 0; step < 20; ++step) {
      t += 50;
      const float wave = (step % 6 == 0) ? 1.5f : 0.0f;
      ai.update(t, makePpg(t, 94.0f), makeImu(t, 0.25f, -0.15f, 9.85f), makeGsr(3.4f + wave));
    }
  }
  const float activeProb = ai.latest().probability;
  assert(ai.latest().hasProbability && activeProb >= 0.70f);
  assert(std::strcmp(ai.latest().state, "ATTENTION") == 0);

  // Brief loose contact (3s < 5.2s) -> preserves ATTENTION and last valid probability (no flash to -1 or CALIBRATING)
  for (int sec = 0; sec < 3; ++sec) {
    t += 1000;
    const auto r = ai.update(t, makePpg(t, 0.0f, false, false), makeImu(t), makeGsr(2.0f));
    assert(std::strcmp(r.state, "ATTENTION") == 0);
    assert(r.hasProbability);
    assert(std::fabs(r.probability - activeProb) < 1e-4f);
  }

  // Re-establish contact within 5s -> stays ATTENTION seamlessly without recalibrating
  t += 1000;
  const auto rBack = ai.update(t, makePpg(t, 94.0f), makeImu(t, 0.25f, -0.15f, 9.85f), makeGsr(3.4f));
  assert(std::strcmp(rBack.state, "ATTENTION") == 0);
  assert(rBack.hasProbability);

  // Remove strap for >= 5.2s -> resets window cleanly to UNCERTAIN
  for (int sec = 0; sec < 7; ++sec) {
    t += 1000;
    ai.update(t, makePpg(t, 0.0f, false, false), makeImu(t), makeGsr(2.0f));
  }
  assert(std::strcmp(ai.latest().state, "UNCERTAIN") == 0);
  assert(!ai.latest().hasProbability);
  assert(ai.latest().windowSeconds == 0);
  std::cout << "[PASS] testFiveSecondGracePreservesStateAndProbabilityThenResetsCleanly\n";
}

int main() {
  testHrStabilityFilter();
  testImpactDetector();
  testSweatyHandsAndQuietStudyingVsRealStress();
  testMildSingleChannelDoesNotTriggerAttention();
  testRepeatedImpactTriggersAttention();
  testUncalibratedGroveGsrSeveritySpread();
  testSmoothProbabilityAndCleanAttentionExit();
  testHrvAndGyroscopeIntelligence();
  testInPlaceResetRestoresCleanCalibrationWithoutStackTemporary();
  testNoFalseNormalOrCalibratingBeforeWristContact();
  testFiveSecondGracePreservesStateAndProbabilityThenResetsCleanly();
  std::cout << "ALL 11 NATIVE EDGE AI UPGRADE TESTS PASSED!\n";
  return 0;
}

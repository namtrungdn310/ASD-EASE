#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <climits>

namespace asd {

// Fast RR estimate adapted from the 0.2.0 firmware.
// This is the selected HR path; the window-based tracker remains available
// for signal-quality diagnostics, not as a competing HR source.
class PpgBeatTracker {
 public:
  struct Estimate {
    bool valid = false;
    float bpm = 0;
    float instantaneousBpm = 0;
    float peakToPeak = 0;
    uint64_t measuredAtMs = 0;
    uint32_t intervalMs = 0;
    uint8_t acceptedIntervals = 0;
  };

  static constexpr float kMinimumBpm = 40.0f;
  static constexpr float kMaximumBpm = 200.0f;

  void reset() { *this = PpgBeatTracker{}; }

  const Estimate& update(uint32_t ir, uint64_t measuredAtMs) {
    if (hasTime_ && (measuredAtMs <= lastSampleAtMs_ || measuredAtMs - lastSampleAtMs_ > 100))
      reset();
    lastSampleAtMs_ = measuredAtMs;
    hasTime_ = true;

    const float raw = static_cast<float>(ir);
    if (!initialized_) {
      dc_ = raw;
      initialized_ = true;
    } else {
      dc_ = .98f * dc_ + .02f * raw;
    }
    const float ac = raw - dc_;
    const float filtered = kB0 * ac + kB1 * x1_ + kB2 * x2_ - kA1 * y1_ - kA2 * y2_;
    x2_ = x1_; x1_ = ac;
    y2_ = y1_; y1_ = filtered;

    if (filtered > maximum_) maximum_ = filtered;
    else maximum_ -= maximum_ * .006f;
    if (filtered < minimum_) minimum_ = filtered;
    else minimum_ += (0.0f - minimum_) * .006f;
    const float peakToPeak = maximum_ - minimum_;

    if (hasAcceptedBeat_ && measuredAtMs - lastAcceptedAtMs_ > 3500) {
      clearIntervals();
      hasPeak_ = false;
      lastRrMs_ = 0;
    }

    const bool isPeak = previous_ > previous2_ && previous_ >= filtered;
    const float threshold = minimum_ + peakToPeak * .60f;
    const float peakStrength = std::max(0.0f, previous_ - minimum_);
    if (isPeak && previous_ > threshold && peakToPeak >= kMinimumPeakToPeakCounts) {
      if (!hasPeak_) {
        lastPeakAtMs_ = measuredAtMs;
        lastPeakStrength_ = peakStrength;
        hasPeak_ = true;
      } else {
        const uint64_t elapsed = measuredAtMs - lastPeakAtMs_;
        const uint32_t intervalMs = static_cast<uint32_t>(std::min<uint64_t>(elapsed, UINT32_MAX));
        const uint32_t blankingMs = lastRrMs_ == 0 ? kMinimumBlankingMs :
            std::max(kMinimumBlankingMs,
                     std::min(kMaximumBlankingMs, static_cast<uint32_t>(lastRrMs_ * .60f)));
        const float bpm = intervalMs ? 60000.0f / static_cast<float>(intervalMs) : 0.0f;
        const bool nearHalfPreviousRr = lastRrMs_ != 0 &&
            std::llabs(static_cast<long long>(intervalMs) - static_cast<long long>(lastRrMs_ / 2)) < 70;
        const bool weakHalfRrPeak = peakStrength < lastPeakStrength_ * .80f;

        // A sustained faster rhythm must be able to escape the old refractory
        // interval. Require three comparable intervening peaks, one per old RR;
        // an isolated or weaker dicrotic peak cannot shorten the blanking period.
        if (intervalMs < blankingMs && intervalMs >= kMinimumBlankingMs &&
            nearHalfPreviousRr && peakStrength >= lastPeakStrength_ * .85f &&
            peakStrength <= lastPeakStrength_ * 1.18f) {
          if (fasterPeakAtMs_ && measuredAtMs - fasterPeakAtMs_ <= lastRrMs_ + 100 &&
              measuredAtMs - fasterPeakAtMs_ + 100 >= lastRrMs_)
            ++fasterPeakCount_;
          else fasterPeakCount_ = 1;
          fasterPeakAtMs_ = measuredAtMs;
          if (fasterPeakCount_ >= 3) {
            clearIntervals();
            lastRrMs_ = intervalMs;
            acceptInterval(bpm, intervalMs, measuredAtMs, peakToPeak);
            lastPeakAtMs_ = measuredAtMs;
            lastPeakStrength_ = peakStrength;
            fasterPeakCount_ = 0;
            previous2_ = previous_;
            previous_ = filtered;
            result_.peakToPeak = peakToPeak;
            return result_;
          }
        }

        if (elapsed > 1800) {
          lastPeakAtMs_ = measuredAtMs;
          lastPeakStrength_ = peakStrength;
          lastRrMs_ = 0;
          clearIntervals();
        } else if (intervalMs >= blankingMs && bpm >= kMinimumBpm && bpm <= kMaximumBpm &&
                   !(nearHalfPreviousRr && weakHalfRrPeak)) {
          acceptInterval(bpm, intervalMs, measuredAtMs, peakToPeak);
          lastPeakAtMs_ = measuredAtMs;
          lastPeakStrength_ = peakStrength;
          lastRrMs_ = intervalMs;
        }
      }
    }

    previous2_ = previous_;
    previous_ = filtered;
    result_.peakToPeak = peakToPeak;
    return result_;
  }

  const Estimate& estimate() const { return result_; }

 private:
  static constexpr float kB0 = .020083f;
  static constexpr float kB1 = .040167f;
  static constexpr float kB2 = .020083f;
  static constexpr float kA1 = -1.561018f;
  static constexpr float kA2 = .641351f;
  static constexpr float kMinimumPeakToPeakCounts = 50.0f;
  static constexpr uint32_t kMinimumBlankingMs = 250;
  static constexpr uint32_t kMaximumBlankingMs = 650;

  void clearIntervals() {
    fasterPeakAtMs_ = 0;
    fasterPeakCount_ = 0;
    rates_.fill(0);
    rateCount_ = rateHead_ = 0;
    smoothedBpm_ = 0;
    hasSmoothedBpm_ = false;
    hasAcceptedBeat_ = false;
    result_ = {};
  }

  void acceptInterval(float bpm, uint32_t intervalMs, uint64_t at, float peakToPeak) {
    rates_[rateHead_] = bpm;
    rateHead_ = (rateHead_ + 1) % rates_.size();
    if (rateCount_ < rates_.size()) ++rateCount_;

    auto sorted = rates_;
    // At most eight RR values: bounded insertion sort avoids the standard
    // library's 16-element sorting threshold and keeps every access explicit.
    for (size_t i = 1; i < rateCount_; ++i) {
      const float value = sorted[i];
      size_t j = i;
      while (j > 0 && sorted[j - 1] > value) {
        sorted[j] = sorted[j - 1];
        --j;
      }
      sorted[j] = value;
    }
    const float median = rateCount_ % 2 ? sorted[rateCount_ / 2] :
        .5f * (sorted[rateCount_ / 2 - 1] + sorted[rateCount_ / 2]);
    // Use the total duration of RR intervals near the median. The median of
    // individual BPM values can favor one quantized interval (320/340ms at 50Hz).
    // The median still excludes distant intervals; no new peaks are accepted.
    float sumRr = 0;
    size_t contributors = 0;
    const float medianRr = 60000.0f / median;
    for (size_t i = 0; i < rateCount_; ++i) {
      const float rr = 60000.0f / rates_[i];
      if (std::fabs(rr - medianRr) <= .25f * medianRr) {
        sumRr += rr;
        ++contributors;
      }
    }
    const float intervalRate = contributors ? 60000.0f * contributors / sumRr : median;
    smoothedBpm_ = hasSmoothedBpm_ ? .15f * intervalRate + .85f * smoothedBpm_ : intervalRate;
    hasSmoothedBpm_ = true;
    hasAcceptedBeat_ = true;
    lastAcceptedAtMs_ = at;

    result_.acceptedIntervals = static_cast<uint8_t>(rateCount_);
    result_.instantaneousBpm = bpm;
    result_.bpm = smoothedBpm_;
    result_.intervalMs = intervalMs;
    result_.measuredAtMs = at;
    result_.peakToPeak = peakToPeak;
    result_.valid = rateCount_ >= 2;
  }

  std::array<float, 8> rates_{};
  Estimate result_{};
  float dc_ = 0, x1_ = 0, x2_ = 0, y1_ = 0, y2_ = 0;
  float previous_ = 0, previous2_ = 0, maximum_ = 0, minimum_ = 0;
  float lastPeakStrength_ = 0, smoothedBpm_ = 0;
  uint64_t lastSampleAtMs_ = 0, lastPeakAtMs_ = 0, lastAcceptedAtMs_ = 0;
  uint32_t lastRrMs_ = 0;
  uint64_t fasterPeakAtMs_ = 0;
  uint8_t fasterPeakCount_ = 0;
  size_t rateCount_ = 0, rateHead_ = 0;
  bool initialized_ = false, hasTime_ = false, hasPeak_ = false;
  bool hasAcceptedBeat_ = false, hasSmoothedBpm_ = false;
};

}  // namespace asd

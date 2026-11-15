#pragma once
#include "processing/ppg_quality.h"

#ifndef ASD_PPG_HYBRID_ENABLED
#define ASD_PPG_HYBRID_ENABLED 1
#endif
#ifndef ASD_PPG_TRACKER_ENABLED
#define ASD_PPG_TRACKER_ENABLED 1
#endif
#if ASD_PPG_TRACKER_ENABLED && !ASD_PPG_HYBRID_ENABLED
#error "Cycle tracker requires the analysis worker"
#endif

namespace asd {
class PpgRate;
struct PpgHybridStats {
  uint32_t requests=0,overwritten=0,completed=0,accepted=0;
  uint32_t lastWallUs=0,maxWallUs=0,stackFreeBytes=0,selfTestUs=0;
  bool enabled=false,selfTestPassed=false;
  uint32_t workspaceBytes=sizeof(PpgQuality);
  float trackingMassScore=0,trackingEvidence=0,trackingRawBpm=0;
};
struct PpgHybridResult { PpgQuality::Result analysis{}; PpgHybridStats stats{}; };
#if (defined(ARDUINO_ARCH_ESP32) && ASD_PPG_HYBRID_ENABLED) || defined(ASD_PPG_NATIVE_HYBRID_TEST)
bool ppgHybridSetup();
bool ppgHybridSubmit(const PpgRate&,uint64_t measuredAt,uint32_t generation);
bool ppgHybridLatest(PpgHybridResult&);
PpgHybridStats ppgHybridStats();
#else
// Native baseline tests và bản tắt quality không giả đã có task/cửa sổ hợp lệ.
inline bool ppgHybridSetup() { return false; }
inline bool ppgHybridSubmit(const PpgRate&,uint64_t,uint32_t) { return false; }
inline bool ppgHybridLatest(PpgHybridResult&) { return false; }
inline PpgHybridStats ppgHybridStats() { return {}; }
#endif
} // namespace asd

#pragma once
#include "board_config.h"
#include "EMA.h"

// =============================================================================
// GSR Sensor — Galvanic Skin Response (Electrodermal Activity - EDA)
// =============================================================================

struct GSRData {
  uint16_t  rawADC                 = 0;
  uint32_t  rawVoltage_mV          = 0;       // Điện áp thô quy đổi từ ADC (mV)
  float     rawVoltage             = 0.0f;    // Điện áp thô (V)
  float     rawConductance_uS      = 0.0f;    // Độ dẫn da thô chưa lọc (µS)

  uint32_t  voltage_mV             = 0;       // Điện áp sau lọc EMA (mV)
  float     voltage                = 0.0f;    // Điện áp sau lọc EMA (V)
  float     resistance             = 0.0f;    // Trở kháng da (Ω)
  float     conductance_uS         = 0.0f;    // Độ dẫn da Conductance sau lọc EMA (µS)
  float     baselineVoltage_mV     = 0.0f;    // Baseline điện áp phiên đo (mV)
  float     baselineConductance_uS = 0.0f;    // Baseline độ dẫn phiên đo (µS)
  float     deltaConductance_uS    = 0.0f;    // Độ lệch độ dẫn so với baseline (µS)
  float     percentChange          = 0.0f;    // % thay đổi so với baseline (%)
  GSRStatus status                 = GSRStatus::DISCONNECTED;
  bool      thresholdExceeded      = false;   // Cờ phản ứng kích thích giao cảm (SCR / Arousal)
  bool      valid                  = false;
};

class GSRSensor {
 public:
  Availability begin();
  GSRData      read();
  bool isReady() const { return ready_; }
  GSRStatus getStatus() const { return status_; }
  void resetBaseline();

 private:
  bool          ready_               = false;
  int           pin_                 = PIN_GSR_ADC;
  GSRStatus     status_              = GSRStatus::DISCONNECTED;

  // Session Baseline Calibration
  bool          isCalibrating_       = false;
  unsigned long calibrationStartMs_  = 0;
  uint64_t      calibMvSum_          = 0;
  uint32_t      calibSampleCount_    = 0;
  float         baselineMv_          = 0.0f;
  float         baselineConductance_ = 0.0f;

  // Bộ lọc EMA chống rung nhiễu ADC và độ dẫn
  EMA           voltageFilter_{GSR_EMA_ALPHA_VOLTAGE};
  EMA           conductanceFilter_{GSR_EMA_ALPHA_CONDUCTANCE};
};

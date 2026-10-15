#pragma once
#include "board_config.h"
#include "EMA.h"

// Forward-declare the SparkFun library class to keep this header lightweight.
class MAX30105;

// =============================================================================
// MAX30102 Sensor — Heart-Rate / SpO2 PPG
// =============================================================================

struct MAX30102Data {
  uint32_t  irValue        = 0;
  uint32_t  redValue       = 0;
  float     rawHeartRate    = 0.0f;                      // Nhịp tim thô trung bình trượt (BPM)
  float     medianHeartRate = 0.0f;                      // Nhịp tim sau bộ lọc Trung vị khoảng RR (BPM)
  float     heartRate       = 0.0f;                      // Nhịp tim sau Trung vị + EMA nhẹ (BPM)
  float     rawSpO2         = 0.0f;                      // SpO2 thô tức thời (%)
  float     spO2            = 0.0f;                      // Nồng độ oxy trong máu sau lọc EMA nhẹ (%)
  float     pulseAmplitude  = 0.0f;                      // Biên độ AC đỉnh-đáy (counts)
  PPGStatus status          = PPGStatus::DISCONNECTED;   // Trạng thái tiếp xúc & đo đạc
  bool      fingerDetected  = false;                     // Đã đặt ngón tay hay chưa
  bool      valid           = false;                     // Dữ liệu nhịp tim và SpO2 đã ổn định
};

class MAX30102Sensor {
 public:
  Availability begin();
  MAX30102Data read();
  bool isReady() const { return ready_; }
  PPGStatus getStatus() const { return status_; }
  void resetCalculations();

 private:
  bool  detectBeat(uint32_t irValue, unsigned long now);
  float computeMedianBpm();   // Tính trung vị khoảng RR từ mảng rates_[]

  bool          ready_        = false;
  PPGStatus     status_       = PPGStatus::DISCONNECTED;
  MAX30105*     sensor_       = nullptr;
  unsigned long lastRetryMs_  = 0;
  uint32_t      latestIr_     = 0;
  uint32_t      latestRed_    = 0;

  static constexpr size_t kRateBufferSize   = 4;
  static constexpr size_t kSampleBufferSize = 50;
  static constexpr size_t kFifoBufferSize   = 32;

  // Thuật toán đo nhịp tim thích ứng 32-bit (chống tràn số 18-bit PPG)
  float         irDc_         = 0.0f;
  float         acSmoothed_   = 0.0f;
  float         prevAc_       = 0.0f;
  float         prev2Ac_      = 0.0f;
  float         acMax_        = 0.0f;
  float         acMin_        = 0.0f;
  unsigned long lastBeatMs_   = 0;
  float         rates_[kRateBufferSize] = {0};
  uint8_t       rateSpot_     = 0;
  float         beatAvg_       = 0.0f;   // Trung bình trượt RR (giá trị thô trước lọc)
  float         medianBpm_     = 0.0f;   // Kết quả trung vị khoảng RR
  size_t        validBeatCount_ = 0;

  // Thuật toán đo SpO2
  uint32_t irBuffer_[kSampleBufferSize]  = {0};
  uint32_t redBuffer_[kSampleBufferSize] = {0};
  size_t   bufferIdx_   = 0;
  size_t   bufferCount_ = 0;
  float    spo2Avg_     = 0.0f;
  float    rawSpo2_     = 0.0f;

  // Bộ lọc HR: Trung vị khoảng RR (loại bỏ nhịp bất thường) + EMA nhẹ (làm mượt hiển thị)
  // Bộ lọc SpO2: EMA nhẹ (làm mượt không làm biến dạng đỉnh sóng)
  EMA      hrFilter_{PPG_EMA_ALPHA_HR};
  EMA      spo2Filter_{PPG_EMA_ALPHA_SPO2};
};

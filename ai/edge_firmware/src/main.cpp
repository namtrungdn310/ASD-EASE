#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>

#include "board_config.h"
#include "HardwareProfiler.h"
#include "MAX30102Sensor.h"
#include "processing/ppg_wrist.h"
#include "processing/ppg_wrist_motion.h"
#include "MPU6050Sensor.h"
#include "GSRSensor.h"
#include "EMA.h"
#include "communication/mqtt_transport.h"
#include "communication/telemetry_serializer.h"
#include "communication/network_settings.h"
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <atomic>

// =============================================================================
// Các đối tượng cảm biến dùng chung
// =============================================================================
static MAX30102Sensor ppgSensor;
static MPU6050Sensor  imuSensor;
static GSRSensor      gsrSensor;
static void observeMotion(const MPU6050Data& imu) {
  asd::PpgMotionSample sample{};sample.at=imu.sampleMonotonicMs;
  sample.valid=imu.valid && imu.hasSampleTimestamp && imu.gyroCalibrated;
  sample.axes={{imu.rawAx/9.80665f,imu.rawAy/9.80665f,imu.rawAz/9.80665f,
      imu.rawGx_deg/90,imu.rawGy_deg/90,imu.rawGz_deg/90}};
  for(float v:sample.axes)sample.valid=sample.valid && std::isfinite(v);
  ppgSensor.addMotionSample(sample);
}


// Mốc đọc riêng cho từng cảm biến
static uint32_t lastPpgReadMs = 0;
static uint32_t lastImuReadMs = 0;
static uint32_t lastGsrReadMs = 0;
static uint32_t lastOutputMs  = 0;

static constexpr unsigned long kPpgIntervalMs    = LOOP_INTERVAL_MS;
static constexpr unsigned long kImuIntervalMs    = LOOP_INTERVAL_MS;
static constexpr unsigned long kGsrIntervalMs    = 1000UL / GSR_SAMPLE_RATE_HZ;
static constexpr unsigned long kOutputIntervalMs = DEFAULT_OUTPUT_INTERVAL_MS;

static OutputFormat outputFormat = DEFAULT_OUTPUT_FORMAT;

// =============================================================================
// Quét và chẩn đoán bus I2C
// =============================================================================
static void scanI2CBuses() {
  Serial.printf("\n--- I2C Bus 0 (SDA=GPIO%d, SCL=GPIO%d) ---\n",
                PIN_MAX30102_SDA, PIN_MAX30102_SCL);
  uint8_t found0 = 0;
  for (uint8_t addr = 1; addr < 127; ++addr) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  [+] 0x%02X", addr);
      if (addr == I2C_ADDR_MAX30102) Serial.print(" -> MAX30102");
      Serial.println();
      ++found0;
    }
  }
  Serial.printf("  Tổng: %u thiết bị\n", found0);

  Serial.printf("\n--- I2C Bus 1 (SDA=GPIO%d, SCL=GPIO%d) ---\n",
                PIN_MPU6050_SDA, PIN_MPU6050_SCL);
  uint8_t found1 = 0;
  for (uint8_t addr = 1; addr < 127; ++addr) {
    Wire1.beginTransmission(addr);
    if (Wire1.endTransmission() == 0) {
      Serial.printf("  [+] 0x%02X", addr);
      if (addr == 0x68 || addr == 0x69) Serial.print(" -> MPU6050");
      Serial.println();
      ++found1;
    }
  }
  Serial.printf("  Tổng: %u thiết bị\n", found1);
  Serial.println(F("----------------------------------------\n"));
}

static const char* getBusHealthString(const MAX30102Data& ppg, const MPU6050Data& imu) {
  // Log chỉ đọc snapshot; task log tuyệt đối không truy cập Wire/Wire1.
  if (ppg.status == PPGStatus::DISCONNECTED || imu.status == IMUStatus::DISCONNECTED)
    return "Chưa đủ cảm biến";
  if (ppg.status == PPGStatus::ERROR || imu.status == IMUStatus::ERROR) return "Có lỗi đọc";
  return "Đang đọc";
}

// =============================================================================
// Helper: trạng thái cảm biến thành chuỗi ngắn gọn
// =============================================================================
static const char* gsrStatusStr(GSRStatus s) {
  switch (s) {
    case GSRStatus::VALID:        return "VALID";
    case GSRStatus::CALIBRATING:  return "CALIBRATING";
    case GSRStatus::SATURATED:    return "SATURATED";
    case GSRStatus::DISCONNECTED: return "DISCONNECTED";
    default:                      return "ERROR";
  }
}

static const char* ppgStatusStr(PPGStatus s) {
  switch (s) {
    case PPGStatus::VALID:            return "VALID";
    case PPGStatus::PULSE_ACQUIRING:  return "ACQUIRING";
    case PPGStatus::NO_FINGER:        return "NO_FINGER";
    case PPGStatus::DISCONNECTED:     return "DISCONNECTED";
    default:                          return "ERROR";
  }
}

static const char* imuStatusStr(IMUStatus s) {
  switch (s) {
    case IMUStatus::VALID:        return "VALID";
    case IMUStatus::CALIBRATING:  return "CALIBRATING";
    case IMUStatus::DISCONNECTED: return "DISCONNECTED";
    default:                      return "ERROR";
  }
}

// =============================================================================
// 1. Serial Monitor — Formatted Text (ngắn gọn, chỉ giá trị sau lọc)
// =============================================================================
static void emitPrettyText(const MAX30102Data& ppg,
                           const MPU6050Data&  imu,
                           const GSRData&      gsr,
                           unsigned long       now) {
  Serial.println(F("\n================================================================"));
  Serial.printf(" ASD-EASE | %s | Uptime: %.1fs | I2C: %s\n",
                MQTT_DEVICE_ID, now / 1000.0f, getBusHealthString(ppg, imu));
  Serial.println(F("----------------------------------------------------------------"));

  // ── [1] GSR — Điện da ──────────────────────────────────────────────────────
  Serial.printf(" [GSR]  %s", gsrStatusStr(gsr.status));
  if (gsr.status == GSRStatus::VALID) {
    Serial.printf("  | ADC=%u", gsr.rawADC);
    if (gsr.voltageCalibrated) Serial.printf(" | V=%.3f V", gsr.voltage);
    else Serial.print(" | ADC chưa có hiệu chuẩn điện áp");
    if (gsr.conductanceCalibrated) Serial.printf(" | G=%.2f µS", gsr.conductance_uS);
    else Serial.print(" | µS chưa hiệu chuẩn mạch");
  } else if (gsr.status == GSRStatus::CALIBRATING) {
    Serial.printf("  |  V = %.3f V  |  Baseline đang thiết lập...", gsr.voltage);
  } else if (gsr.status == GSRStatus::DISCONNECTED) {
    Serial.print("  |  Chưa đeo điện cực");
  } else if (gsr.status == GSRStatus::SATURATED) {
    Serial.printf("  |  V = %.3f V  |  Bão hòa", gsr.rawVoltage);
  }
  Serial.println();

  // ── [2] MAX30102 — Tim mạch & SpO2 ────────────────────────────────────────
  Serial.printf(" [PPG]  %s", ppgStatusStr(ppg.status));
  if (ppg.status == PPGStatus::VALID) {
    Serial.printf("  |  HR = %.1f BPM (cửa sổ8s)", ppg.heartRate);
  } else if (ppg.status == PPGStatus::PULSE_ACQUIRING) {
    if (ppg.heartRate >= HR_MIN_PHYSIOLOGICAL) {
      Serial.printf("  |  HR ~ %.1f BPM (đang ổn định...)", ppg.heartRate);
    } else {
      Serial.print("  |  Đang bắt xung mạch...");
    }
  } else if (ppg.status == PPGStatus::NO_FINGER) {
    Serial.print("  |  Chưa xác nhận tiếp xúc da");
    // Đối chiếu tiếp xúc thực với ngưỡng; không thay thuật toán hoặc gói MQTT.
    Serial.printf("  |  IR=%lu  RED=%lu  nguongIR=%lu",
                  static_cast<unsigned long>(ppg.irValue),
                  static_cast<unsigned long>(ppg.redValue),
                  static_cast<unsigned long>(PPG_IR_FINGER_THRESHOLD));
  } else {
    Serial.print("  |  Lỗi đọc hoặc tín hiệu chưa hợp lệ");
  }
  Serial.println();

  // ── [3] MPU6050 — Gia tốc & Con quay ──────────────────────────────────────
  Serial.printf(" [IMU]  %s", imuStatusStr(imu.status));
  if (imu.valid) {
    Serial.printf("  |  Ax=%+.2f  Ay=%+.2f  Az=%+.2f m/s²  |a|=%.2f",
                  imu.ax, imu.ay, imu.az, imu.accelMagnitude);
    if (imu.movementValid) Serial.printf("  movement=%.3f", imu.movementScore);
    else Serial.print("  movement=chua_du_mau");
    Serial.println();
    Serial.printf("         |  Gx=%+.1f  Gy=%+.1f  Gz=%+.1f °/s",
                  imu.gx_deg, imu.gy_deg, imu.gz_deg);
    if (std::isfinite(imu.temperature)) Serial.printf(" | T=%.1f°C", imu.temperature);
  } else if (imu.status == IMUStatus::CALIBRATING) {
    Serial.print("  | Giữ yên để lấy lệch gyro; chưa gửi vector hợp lệ");
  } else {
    Serial.print("  | Chưa có vector hợp lệ, xem ID/cấu hình/I2C");
  }
  Serial.println();

  Serial.println(F("================================================================"));
}

// =============================================================================
// 2. JSON output (ngắn gọn, chỉ giá trị sau lọc)
// =============================================================================
static void emitPrettyJson(const MAX30102Data& ppg,
                           const MPU6050Data&  imu,
                           const GSRData&      gsr,
                           unsigned long       now) {
  JsonDocument doc;

  doc["uptime_ms"] = now;
  doc["device"]    = MQTT_DEVICE_ID;

  // GSR
  JsonObject g = doc["gsr"].to<JsonObject>();
  g["status"]  = gsrStatusStr(gsr.status);
  g["valid"]   = gsr.valid;
  g["adc_raw"] = gsr.rawADC;
  g["voltage_calibrated"] = gsr.voltageCalibrated;
  g["conductance_calibrated"] = gsr.conductanceCalibrated;
  if (gsr.status == GSRStatus::VALID || gsr.status == GSRStatus::CALIBRATING) {
    if (gsr.voltageCalibrated) {
    g["voltage_v"]       = roundf(gsr.voltage * 1000.0f) / 1000.0f;
    g["voltage_mv"]      = gsr.voltage_mV;
    }
    if (gsr.conductanceCalibrated) {
    g["resistance_ohm"]  = roundf(gsr.resistance);
    g["conductance_us"]  = roundf(gsr.conductance_uS * 100.0f) / 100.0f;
    }
    if (gsr.valid) {
      g["baseline_mv"]   = roundf(gsr.baselineVoltage_mV * 10.0f) / 10.0f;
      g["delta_us"]      = roundf(gsr.deltaConductance_uS * 100.0f) / 100.0f;
    }
  }

  // MAX30102
  JsonObject p = doc["ppg"].to<JsonObject>();
  p["status"]  = ppgStatusStr(ppg.status);
  p["valid"]   = ppg.valid;
  p["finger"]  = ppg.fingerDetected;
  if (ppg.fingerDetected && ppg.heartRate >= HR_MIN_PHYSIOLOGICAL) {
    p["hr_bpm"]      = roundf(ppg.heartRate * 10.0f) / 10.0f;
  }

  // MPU6050
  JsonObject m = doc["imu"].to<JsonObject>();
  m["status"] = imuStatusStr(imu.status);
  m["valid"]  = imu.valid;
  if (imu.valid) {
    JsonObject a = m["accel_ms2"].to<JsonObject>();
    a["x"] = roundf(imu.ax * 100.0f) / 100.0f;
    a["y"] = roundf(imu.ay * 100.0f) / 100.0f;
    a["z"] = roundf(imu.az * 100.0f) / 100.0f;
    a["mag"] = roundf(imu.accelMagnitude * 100.0f) / 100.0f;

    JsonObject gy = m["gyro_dps"].to<JsonObject>();
    gy["x"] = roundf(imu.gx_deg * 10.0f) / 10.0f;
    gy["y"] = roundf(imu.gy_deg * 10.0f) / 10.0f;
    gy["z"] = roundf(imu.gz_deg * 10.0f) / 10.0f;

    m["temp_c"] = roundf(imu.temperature * 10.0f) / 10.0f;
  }

  serializeJsonPretty(doc, Serial);
  Serial.println();
}

static void emitOutput(const MAX30102Data& ppg,
                       const MPU6050Data&  imu,
                       const GSRData&      gsr,
                       unsigned long       now, OutputFormat format) {
  if (format == OutputFormat::PRETTY_JSON) {
    emitPrettyJson(ppg, imu, gsr, now);
  } else {
    emitPrettyText(ppg, imu, gsr, now);
  }
}

struct DiagnosticSnapshot {
  MAX30102Data ppg;
  MPU6050Data imu;
  GSRData gsr;
  MqttStats net;
  PpgAcquisitionStats ppgStats;
  ImuAcquisitionStats imuStats;
  std::array<float, 3> gyroOffsets;
  uint32_t now;
  OutputFormat format;
  asd::PpgHybridStats hybrid;
};
static QueueHandle_t diagnosticQueue = nullptr;
struct PpgTraceFrame {
  uint64_t time; uint32_t red,ir;
  asd::PpgMotionSample motion;
  uint8_t redLed,irLed;uint32_t exposureGeneration;
};
static QueueHandle_t ppgTraceQueue = nullptr;
static std::atomic<uint32_t> traceStarted{0}, traceDropped{0};
static void observePpg(uint64_t measured, uint32_t red, uint32_t ir) {
  const uint32_t started = traceStarted.load();
  if (!ppgTraceQueue || started == 0 || uint32_t(millis() - started) >= 60000) return;
  const PpgTraceFrame frame{measured,red,ir,ppgSensor.motionAt(measured),
      ppgSensor.redLed(),ppgSensor.irLed(),ppgSensor.exposureGeneration()};
  if (xQueueSend(ppgTraceQueue, &frame, 0) != pdTRUE) ++traceDropped;
}

static void diagnosticTask(void*) {
  DiagnosticSnapshot d{};
  for (;;) {
    const bool haveDiagnostic = xQueueReceive(diagnosticQueue, &d, pdMS_TO_TICKS(10)) == pdTRUE;
    if (!Serial) { if (ppgTraceQueue) xQueueReset(ppgTraceQueue); continue; }
    PpgTraceFrame frame{};
    for (unsigned i = 0; ppgTraceQueue && i < 16 &&
         xQueueReceive(ppgTraceQueue, &frame, 0) == pdTRUE; ++i)
      Serial.printf("[PPG-RAW] t=%llu red=%lu ir=%lu imu=%llu,%u,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f led=%u,%u,%lu\n",
        frame.time,frame.red,frame.ir,frame.motion.at,unsigned(frame.motion.valid),
        frame.motion.axes[0],frame.motion.axes[1],frame.motion.axes[2],
        frame.motion.axes[3],frame.motion.axes[4],frame.motion.axes[5],
        unsigned(frame.redLed),unsigned(frame.irLed),frame.exposureGeneration);
    if (!haveDiagnostic) continue;
    emitOutput(d.ppg, d.imu, d.gsr, d.now, d.format);
    const auto& s = d.net;
    Serial.printf("[NET] wifi=%u mqtt=%u sync=%u tx=%lu fail=%lu drop=%lu invalid=%lu heapMin=%lu stackWater=%lu loopGap=%lu samples=%lu/%lu/%lu controlDrop=%lu pending=%lu outbox=%lu error=%d fatal=%d\n",
      s.wifiConnected, s.mqttConnected, s.synchronized, s.publishOk, s.publishFail, s.dropped,
      s.invalid, s.minHeapBytes, s.networkStackHighWater, s.maxLoopGapMs, s.ppgSamples, s.imuSamples, s.gsrSamples,
      s.controlDropped, s.pendingControl, s.outboxBytes, s.transportError, s.fatalReason);
    Serial.printf("[NET-LINK] rssiDbm=%d reconnects=%lu errorAtMs=%lu mqttErrorType=%d tlsStackError=%d socketError=%d\n",
      s.wifiRssiDbm, s.reconnects, s.transportErrorAtMs,
      s.mqttErrorType, s.tlsStackError, s.socketError);
    const auto& p = d.ppgStats;
    Serial.printf("[PPG-OPT] redLed=%u irLed=%u changes=%lu settling=%u irEvidence=%.3f redEvidence=%.3f sqi=%.3f imuCoverage=%.3f overlap=%.3f corrected=%u supported=%u\n",
      unsigned(d.ppg.redLed),unsigned(d.ppg.irLed),d.ppg.exposureChanges,unsigned(d.ppg.exposureSettling),
      d.ppg.irEvidence,d.ppg.redEvidence,d.ppg.qualityEvidence,d.ppg.motionCoverage,d.ppg.motionOverlap,
      unsigned(d.ppg.motionCorrected),unsigned(d.ppg.motionSupported));
    Serial.printf("[PPG-DAQ] ms=%lu n=%lu batchMax=%lu pollMax=%lu io=%lu overflow=%lu lostMin=%lu gaps=%lu clip=%lu IR=%lu RED=%lu ac=%.1f hr=%.1f valid=%u fw=%s\n",
      d.now, p.samples, p.maxBatch, p.maxPollGapMs, p.ioErrors, p.overflowEvents,
      p.overflowSamplesLowerBound, p.gapEvents, p.clippedSamples,
      d.ppg.irValue, d.ppg.redValue, d.ppg.pulseAmplitude,
      d.ppg.heartRate, unsigned(d.ppg.valid), ASD_FIRMWARE_VERSION);
    Serial.printf("[PPG-REG] wr=%u rd=%u ovf=%u int=0x%02X discarded=%lu contact=%u settled=%u restarts=%lu windows=%lu\n",
      p.writePointer, p.readPointer, p.overflowCounter, p.interrupt, p.discardedSamples,
      unsigned(d.ppg.fingerDetected), unsigned(d.ppg.contactSettled), p.contactRestarts, d.ppg.acceptedWindows);
    Serial.printf("[PPG-RATE] ir=%.3f recent=%.3f red=%.3f redRecent=%.3f source=%u powerRatio=%.2f maxUs=%lu\n",
      d.ppg.periodicity, d.ppg.recentPeriodicity, d.ppg.redPeriodicity, d.ppg.redRecentPeriodicity,
      unsigned(d.ppg.heartRateSource), d.ppg.bandPowerRatio, p.maxRateProcessingUs);
    Serial.printf("[PPG-INIT] attempts=%lu ok=%lu failed=%lu started=%lu duration=%lu maxDuration=%lu lastRecovery=%lu retryMs=%lu stepMaxUs=%lu\n",
      p.initAttempts, p.initSuccesses, p.initFailures, p.lastInitStartedMs,
      p.lastInitDurationMs, p.maxInitDurationMs, p.lastRecoveryDurationMs, I2C_RETRY_INTERVAL_MS,p.maxInitStepUs);
    const auto& f = p.lastFault;
    Serial.printf("[PPG-IO] events=%lu at=%lu phase=%u kind=%u reg=0x%02X requested=%u received=%u code=%u expected=0x%02X observed=0x%02X\n",
      p.faultEvents, f.atMs, unsigned(f.phase), unsigned(f.kind), unsigned(f.reg),
      unsigned(f.requested), unsigned(f.received), unsigned(f.code), unsigned(f.expected), unsigned(f.observed));
    const auto& h=d.hybrid;
    const auto& cause=p.recoveryCause;
    Serial.printf("[PPG-CAUSE] at=%lu phase=%u kind=%u reg=0x%02X requested=%u received=%u code=%u\n",
      cause.atMs,unsigned(cause.phase),unsigned(cause.kind),unsigned(cause.reg),
      unsigned(cause.requested),unsigned(cause.received),unsigned(cause.code));
    const auto optics=asd::assessWrist(d.ppg.irValue,d.ppg.pulseAmplitude,d.ppg.hasRateWindow,
      d.ppg.fingerDetected,d.ppg.contactSettled,d.ppg.opticalOverload,d.ppg.valid);
    const char* opticalLevel=asd::wristLevelName(optics.level);
#if ASD_PPG_WRIST_MOTION_GUARD
    if (d.ppg.fingerDetected && !d.ppg.opticalOverload && !d.ppg.wristMotionAllowed)
      opticalLevel=d.ppg.wristMotionReason==0 ? "IMU_CHUA_SAN_SANG" :
        (d.ppg.wristMotionReason==1 ? "DANG_CHUYEN_DONG" : "DANG_THU_LAI_CUA_SO");
#endif
    Serial.printf("[PPG-WRIST] level=%s acDcPct=%.4f ambientEvents=%lu led=%u chipHz=%u fifoHz=%u motionReason=%u allowHr=%u motionScore=%.4f\n",
      opticalLevel,optics.acDcPct,p.ambientOverflowEvents,
      unsigned(d.ppg.irLed),PPG_RAW_SAMPLE_RATE_HZ,PPG_EFFECTIVE_RATE_HZ,
      unsigned(d.ppg.wristMotionReason),unsigned(d.ppg.wristMotionAllowed),d.imu.movementScore);
    Serial.printf("[PPG-HYBRID] enabled=%u selfTest=%u requests=%lu overwritten=%lu completed=%lu accepted=%lu wallUs=%lu maxWallUs=%lu stackFree=%lu selfTestUs=%lu workspace=%u\n",
      unsigned(h.enabled),unsigned(h.selfTestPassed),h.requests,h.overwritten,h.completed,h.accepted,
      h.lastWallUs,h.maxWallUs,h.stackFreeBytes,h.selfTestUs,unsigned(h.workspaceBytes));
#if ASD_PPG_TRACKER_ENABLED
    Serial.printf("[PPG-TRACK] massScore=%.3f evidence=%.3f candidateBpm=%.2f enabled=%u\n",
      h.trackingMassScore,h.trackingEvidence,h.trackingRawBpm,unsigned(h.enabled));
#endif
    const auto& m = d.imuStats;
    Serial.printf("[IMU-DAQ] ms=%lu n=%lu io=%lu overflow=%lu gaps=%lu clip=%lu bias=%u offsets=%.3f/%.3f/%.3f logStack=%u\n",
      d.now, m.samples, m.ioErrors, m.overflowEvents, m.gaps, m.clipped,
      unsigned(d.imu.gyroCalibrated), d.gyroOffsets[0], d.gyroOffsets[1], d.gyroOffsets[2],
      unsigned(uxTaskGetStackHighWaterMark(nullptr)));
    if (traceStarted.load() != 0)
      Serial.printf("[PPG-TRACE] dropped=%lu\n", static_cast<unsigned long>(traceDropped.load()));
  }
}

// =============================================================================
void setup() {
  imuSensor.setSampleObserver(observeMotion);
  Serial.begin(115200);
  delay(1500);

  Serial.println(F("\n========================================================"));
  Serial.println(F("  ASD-EASE Edge Firmware v" FIRMWARE_VERSION));
  Serial.println(F("  Board: ESP32-S3 Super Mini"));
  Serial.println(F("========================================================"));
  Serial.println(F("  Gõ 'j' -> JSON  |  't' -> Text\n"));

  // ── Khởi tạo 2 Bus I2C phần cứng độc lập ──────────────────────────────────
  Serial.printf("[I2C0] MAX30102  SDA=GPIO%d  SCL=GPIO%d  %lu kHz\n",
                PIN_MAX30102_SDA, PIN_MAX30102_SCL, I2C_CLOCK_HZ / 1000UL);
  Wire.begin(PIN_MAX30102_SDA, PIN_MAX30102_SCL);
  Wire.setClock(I2C_CLOCK_HZ);
  Wire.setTimeOut(I2C_TIMEOUT_MS);

  Serial.printf("[I2C1] MPU6050   SDA=GPIO%d  SCL=GPIO%d  %lu kHz\n",
                PIN_MPU6050_SDA, PIN_MPU6050_SCL, I2C_CLOCK_HZ / 1000UL);
  Wire1.begin(PIN_MPU6050_SDA, PIN_MPU6050_SCL);
  Wire1.setClock(I2C_CLOCK_HZ);
  Wire1.setTimeOut(I2C_TIMEOUT_MS);

  scanI2CBuses();

  // ── Khởi tạo 3 cảm biến ───────────────────────────────────────────────────
  Availability s1 = ppgSensor.begin();
  Availability s2 = imuSensor.begin(&Wire1);
  Availability s3 = gsrSensor.begin();

  Serial.printf("\n[INIT] MAX30102: %s | MPU6050 (0x%02X): %s | GSR (GPIO%d): %s\n",
                s1 == Availability::READY ? "OK" : (ppgSensor.isInitializing() ? "DANG_KHOI_TAO" : "FAIL"),
                imuSensor.getAddress(),
                s2 == Availability::READY ? "OK" :
                  (imuSensor.getStatus() == IMUStatus::CALIBRATING ? "DANG_KHOI_TAO" : "FAIL"),
                PIN_GSR_ADC,
                s3 == Availability::READY ? "OK" : "FAIL");
  Serial.println(F("[NOTE] MPU6050 lắp úp -> trục Y,Z đã đảo chiều trong firmware\n"));

  const unsigned long now = millis();
  lastPpgReadMs = lastImuReadMs = lastGsrReadMs = lastOutputMs = now;

  // ── Hien thi cau hinh mang da compile ────────────────────────────────────
  Serial.println(F("[CONFIG] ===== NETWORK CONFIG ======"));
  Serial.printf("[CONFIG] SSID='%s' DEVICE='%s'\n", WIFI_SSID, MQTT_DEVICE_ID);
  Serial.printf("[CONFIG] MQTT=%s:%d USER='%s'\n", MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME);
  Serial.printf("[CONFIG] NETWORK=%d TLS=%d INSECURE_LAN=%d\n", ASD_NETWORK_ENABLED, MQTT_USE_TLS, ASD_ALLOW_INSECURE_LAN);
  Serial.println(F("[CONFIG] =============================="));

  // ── MQTT transport ──────────────────────────────────────────────────────────
  mqttTransportSetup();
  if (!asd::ppgHybridSetup()) {
#if ASD_PPG_TRACKER_ENABLED
    Serial.println(F("[PPG-HYBRID] Task tracker chưa bật; HR chờ task, không thay bằng số đối chứng"));
#else
    Serial.println(F("[PPG-HYBRID] Task chưa bật; tiếp tục bộ HR đối chứng"));
#endif
  }
  if (ASD_SERIAL_DIAGNOSTICS) {
    ppgTraceQueue = xQueueCreate(128, sizeof(PpgTraceFrame));
    diagnosticQueue = xQueueCreate(1, sizeof(DiagnosticSnapshot));
    if (diagnosticQueue && xTaskCreate(diagnosticTask, "asd-log", 6144, nullptr, 0, nullptr) != pdPASS) {
      vQueueDelete(diagnosticQueue); diagnosticQueue = nullptr;
    }
    if (!diagnosticQueue) Serial.println(F("[LOG] Không đủ bộ nhớ; tắt log định kỳ, sensing/MQTT vẫn chạy"));
    if (diagnosticQueue && ppgTraceQueue) ppgSensor.setSampleObserver(observePpg);
  }
}

// =============================================================================
void loop() {
  const unsigned long now = millis();

  // Xử lý lệnh phím đổi chế độ hiển thị
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == 'j' || c == 'J') {
      outputFormat = OutputFormat::PRETTY_JSON;
    } else if (c == 't' || c == 'T') {
      outputFormat = OutputFormat::PRETTY_TEXT;
    } else if (c == 'p') {
      traceDropped.store(0); traceStarted.store(millis());
    } else if (c == 'q') {
      traceStarted.store(0); if (ppgTraceQueue) xQueueReset(ppgTraceQueue);
    }
  }

  static MAX30102Data latestPpg;
  static MPU6050Data  latestImu;
  static GSRData      latestGsr;
  static asd::WristMotionGuard wristMotion;
  uint32_t ppgSamples = 0;
  uint32_t imuSamples = 0;
  bool gsrNew = false;


  if (asd::sampleDue(now, lastImuReadMs, kImuIntervalMs)) {
    latestImu = imuSensor.read();
    imuSamples = latestImu.newSamples;
  }
  if (asd::sampleDue(now, lastPpgReadMs, kPpgIntervalMs)) {
    latestPpg = ppgSensor.read();
    ppgSamples = latestPpg.newSamples;
  }

#if ASD_PPG_WRIST_MOTION_GUARD
  const uint64_t motionNow=static_cast<uint64_t>(esp_timer_get_time())/1000;
  // Chỉ vượt cổng chuyển động khi worker có IMU khớp thời gian và
  // ứng viên HR không trùng chu kỳ chuyển động. Không xóa cửa sổ PPG.
  wristMotion.update(motionNow,latestImu.sampleMonotonicMs,
      latestImu.valid && latestImu.hasSampleTimestamp,latestImu.gyroCalibrated,
      latestImu.movementValid,latestImu.movementScore);
  ppgSensor.setExposureQuiet(wristMotion.allowsHr());
  const bool motionReferenceFresh=latestImu.valid && latestImu.gyroCalibrated && latestImu.hasSampleTimestamp &&
      latestImu.sampleMonotonicMs<=motionNow && motionNow-latestImu.sampleMonotonicMs<=100;
  latestPpg.wristMotionAllowed=wristMotion.allowsHr() || (motionReferenceFresh && latestPpg.motionSupported);
  latestPpg.wristMotionReason=static_cast<uint8_t>(wristMotion.reason());
  if (!latestPpg.wristMotionAllowed) {
    latestPpg.valid=false; latestPpg.hasHeartRateTimestamp=false;
    latestPpg.heartRate=0;
    if (latestPpg.status==PPGStatus::VALID) latestPpg.status=PPGStatus::PULSE_ACQUIRING;
  }
#else
  latestPpg.wristMotionAllowed=true;
#endif

  if (asd::sampleDue(now, lastGsrReadMs, kGsrIntervalMs)) {
    latestGsr = gsrSensor.read();
    gsrNew = latestGsr.hasSampleTimestamp;
  }

  // Xuất gói dữ liệu định kỳ
  if (asd::sampleDue(now, lastOutputMs, kOutputIntervalMs) && diagnosticQueue) {
    const DiagnosticSnapshot d{latestPpg, latestImu, latestGsr, mqttGetStats(),
      ppgSensor.acquisitionStats(), imuSensor.acquisitionStats(), imuSensor.gyroOffsets(), now, outputFormat, asd::ppgHybridStats()};
    xQueueOverwrite(diagnosticQueue, &d); // Latest-only, không đợi Serial.
  }

  const uint64_t qualityNow = static_cast<uint64_t>(esp_timer_get_time()) / 1000;
  mqttUpdateSnapshot(captureTelemetrySnapshot(latestPpg, latestImu, latestGsr,
    millis(), qualityNow, ppgSensor.signalQuality(qualityNow), gsrSensor.signalQuality(qualityNow),
    imuSensor.accelerationQuality(qualityNow), imuSensor.rotationQuality(qualityNow)));

  mqttRecordSensing(now, ppgSamples, imuSamples, gsrNew);

  // Điều phối nhịp loop chính
  const unsigned long elapsed = millis() - now;
  if (elapsed < LOOP_INTERVAL_MS) {
    delay(LOOP_INTERVAL_MS - elapsed);
  }
}

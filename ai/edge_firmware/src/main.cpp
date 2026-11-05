#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>

// Include network_config.h TRUC TIEP — khong phu thuoc __has_include cache
#include "network_config.h"

#include "board_config.h"
#include "HardwareProfiler.h"
#include "MAX30102Sensor.h"
#include "MPU6050Sensor.h"
#include "GSRSensor.h"
#include "EMA.h"
#include "communication/mqtt_transport.h"
#include "communication/telemetry_serializer.h"
#include "communication/network_settings.h"
#include <esp_timer.h>

// =============================================================================
// Các đối tượng cảm biến dùng chung
// =============================================================================
static MAX30102Sensor ppgSensor;
static MPU6050Sensor  imuSensor;
static GSRSensor      gsrSensor;

// Mốc đọc riêng cho từng cảm biến
static unsigned long lastPpgReadMs = 0;
static unsigned long lastImuReadMs = 0;
static unsigned long lastGsrReadMs = 0;
static unsigned long lastOutputMs  = 0;

static constexpr unsigned long kPpgIntervalMs    = PPG_SAMPLE_PERIOD_MS;
static constexpr unsigned long kImuIntervalMs    = 1000UL / IMU_SAMPLE_RATE_HZ;
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

static const char* getBusHealthString() {
  Wire.beginTransmission(I2C_ADDR_MAX30102);
  byte errMax = Wire.endTransmission();
  Wire1.beginTransmission(imuSensor.getAddress());
  byte errImu = Wire1.endTransmission();

  if (errMax == 0 && errImu == 0) return "OK";
  if (errMax == 0 && errImu != 0) return "MPU6050 NACK";
  if (errMax != 0 && errImu == 0) return "MAX30102 NACK";
  return "BOTH NACK";
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
                MQTT_DEVICE_ID, now / 1000.0f, getBusHealthString());
  Serial.println(F("----------------------------------------------------------------"));

  // ── [1] GSR — Điện da ──────────────────────────────────────────────────────
  Serial.printf(" [GSR]  %s", gsrStatusStr(gsr.status));
  if (gsr.status == GSRStatus::VALID) {
    Serial.printf("  |  V = %.3f V (%u mV)  |  R = %.1f kΩ  |  G = %.2f µS",
                  gsr.voltage, gsr.voltage_mV,
                  gsr.resistance / 1000.0f, gsr.conductance_uS);
    if (gsr.thresholdExceeded) Serial.print("  ** SCR **");
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
    Serial.printf("  |  HR = %.1f BPM  |  SpO2 = %.1f %%",
                  ppg.heartRate, ppg.spO2);
  } else if (ppg.status == PPGStatus::PULSE_ACQUIRING) {
    if (ppg.heartRate >= HR_MIN_PHYSIOLOGICAL) {
      Serial.printf("  |  HR ~ %.1f BPM (đang ổn định...)", ppg.heartRate);
    } else {
      Serial.print("  |  Đang bắt xung mạch...");
    }
  } else if (ppg.status == PPGStatus::NO_FINGER) {
    Serial.print("  |  Chưa đặt ngón tay");
  } else {
    Serial.print("  |  Mất kết nối I2C");
  }
  Serial.println();

  // ── [3] MPU6050 — Gia tốc & Con quay ──────────────────────────────────────
  Serial.printf(" [IMU]  %s", imuStatusStr(imu.status));
  if (imu.valid) {
    Serial.printf("  |  Ax=%+.2f  Ay=%+.2f  Az=%+.2f m/s²  |a|=%.2f",
                  imu.ax, imu.ay, imu.az, imu.accelMagnitude);
    Serial.println();
    Serial.printf("         |  Gx=%+.1f  Gy=%+.1f  Gz=%+.1f °/s  |  T=%.1f°C",
                  imu.gx_deg, imu.gy_deg, imu.gz_deg, imu.temperature);
  } else {
    Serial.print("  |  Mất kết nối, đang retry...");
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
  if (gsr.status == GSRStatus::VALID || gsr.status == GSRStatus::CALIBRATING) {
    g["voltage_v"]       = roundf(gsr.voltage * 1000.0f) / 1000.0f;
    g["voltage_mv"]      = gsr.voltage_mV;
    g["resistance_ohm"]  = roundf(gsr.resistance);
    g["conductance_us"]  = roundf(gsr.conductance_uS * 100.0f) / 100.0f;
    if (gsr.valid) {
      g["baseline_mv"]   = roundf(gsr.baselineVoltage_mV * 10.0f) / 10.0f;
      g["delta_us"]      = roundf(gsr.deltaConductance_uS * 100.0f) / 100.0f;
      g["scr_event"]     = gsr.thresholdExceeded;
    }
  }

  // MAX30102
  JsonObject p = doc["ppg"].to<JsonObject>();
  p["status"]  = ppgStatusStr(ppg.status);
  p["valid"]   = ppg.valid;
  p["finger"]  = ppg.fingerDetected;
  if (ppg.fingerDetected && ppg.heartRate >= HR_MIN_PHYSIOLOGICAL) {
    p["hr_bpm"]      = roundf(ppg.heartRate * 10.0f) / 10.0f;
    p["spo2_pct"]    = roundf(ppg.spO2 * 10.0f) / 10.0f;
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
                       unsigned long       now) {
  if (outputFormat == OutputFormat::PRETTY_JSON) {
    emitPrettyJson(ppg, imu, gsr, now);
  } else {
    emitPrettyText(ppg, imu, gsr, now);
  }
}

// =============================================================================
void setup() {
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
                s1 == Availability::READY ? "OK" : "FAIL",
                imuSensor.getAddress(),
                s2 == Availability::READY ? "OK" : "FAIL",
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
}

// =============================================================================
void loop() {
  const unsigned long now = millis();

  // Xử lý lệnh phím đổi chế độ hiển thị
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == 'j' || c == 'J') {
      outputFormat = OutputFormat::PRETTY_JSON;
      Serial.println(F("\n>>> Chế độ: JSON <<<"));
    } else if (c == 't' || c == 'T') {
      outputFormat = OutputFormat::PRETTY_TEXT;
      Serial.println(F("\n>>> Chế độ: TEXT <<<"));
    }
  }

  static MAX30102Data latestPpg;
  static MPU6050Data  latestImu;
  static GSRData      latestGsr;
  uint32_t ppgSamples = 0;
  bool imuNew = false, gsrNew = false;


  if (now - lastPpgReadMs >= kPpgIntervalMs) {
    latestPpg = ppgSensor.read();
    ppgSamples = latestPpg.newSamples;
    lastPpgReadMs = now;
  }

  if (now - lastImuReadMs >= kImuIntervalMs) {
    latestImu = imuSensor.read();
    imuNew = latestImu.hasSampleTimestamp;
    lastImuReadMs = now;
  }

  if (now - lastGsrReadMs >= kGsrIntervalMs) {
    latestGsr = gsrSensor.read();
    gsrNew = latestGsr.hasSampleTimestamp;
    lastGsrReadMs = now;
  }

  // Xuất gói dữ liệu định kỳ
  if (now - lastOutputMs >= kOutputIntervalMs) {
    if (ASD_SERIAL_DIAGNOSTICS) emitOutput(latestPpg, latestImu, latestGsr, now);
    if (ASD_SERIAL_DIAGNOSTICS) {
      auto s = mqttGetStats();
      Serial.printf("[NET] wifi=%u mqtt=%u sync=%u tx=%lu fail=%lu drop=%lu invalid=%lu heapMin=%lu stackWater=%lu loopGap=%lu samples=%lu/%lu/%lu controlDrop=%lu pending=%lu outbox=%lu error=%d fatal=%d\n",
        s.wifiConnected, s.mqttConnected, s.synchronized, s.publishOk, s.publishFail, s.dropped,
        s.invalid, s.minHeapBytes, s.networkStackHighWater, s.maxLoopGapMs, s.ppgSamples, s.imuSamples, s.gsrSamples,
        s.controlDropped, s.pendingControl, s.outboxBytes, s.transportError, s.fatalReason);
    }

    lastOutputMs = now;
  }

  mqttUpdateSnapshot(captureTelemetrySnapshot(latestPpg, latestImu, latestGsr,
    millis(), static_cast<uint64_t>(esp_timer_get_time()) / 1000));

  SensorTelemetry st{};
  st.finger = latestPpg.fingerDetected;
  st.hr_bpm = latestPpg.heartRate;
  st.spo2_pct = latestPpg.spO2;
  st.ppg_valid = latestPpg.valid;
  strncpy(st.ppg_status, ppgStatusStr(latestPpg.status), sizeof(st.ppg_status) - 1);

  st.ax = latestImu.ax;
  st.ay = latestImu.ay;
  st.az = latestImu.az;
  st.accel_mag = latestImu.accelMagnitude;
  st.gx_deg = latestImu.gx_deg;
  st.gy_deg = latestImu.gy_deg;
  st.gz_deg = latestImu.gz_deg;
  st.temp_c = latestImu.temperature;
  st.imu_valid = latestImu.valid;
  strncpy(st.imu_status, imuStatusStr(latestImu.status), sizeof(st.imu_status) - 1);

  st.voltage_v = latestGsr.voltage;
  st.voltage_mv = latestGsr.voltage_mV;
  st.resistance_kohm = latestGsr.resistance / 1000.0f;
  st.conductance_us = latestGsr.conductance_uS;
  st.raw_adc = latestGsr.rawADC;
  st.gsr_valid = latestGsr.valid;
  strncpy(st.gsr_status, gsrStatusStr(latestGsr.status), sizeof(st.gsr_status) - 1);

  mqttUpdateSensors(st);
  mqttRecordSensing(now, ppgSamples, imuNew, gsrNew);

  // Điều phối nhịp loop chính
  const unsigned long elapsed = millis() - now;
  if (elapsed < LOOP_INTERVAL_MS) {
    delay(LOOP_INTERVAL_MS - elapsed);
  }
}


#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>

#include "board_config.h"
#include "HardwareProfiler.h"
#include "MAX30102Sensor.h"
#include "MPU6050Sensor.h"
#include "GSRSensor.h"
#include "EMA.h"

// =============================================================================
// Global sensor instances
// =============================================================================
static MAX30102Sensor ppgSensor;
static MPU6050Sensor  imuSensor;
static GSRSensor      gsrSensor;

// Per-sensor sub-sampling timers
static unsigned long lastPpgReadMs = 0;
static unsigned long lastImuReadMs = 0;
static unsigned long lastGsrReadMs = 0;
static unsigned long lastOutputMs  = 0;

static constexpr unsigned long kPpgIntervalMs    = 1000UL / PPG_SAMPLE_RATE_HZ;
static constexpr unsigned long kImuIntervalMs    = 1000UL / IMU_SAMPLE_RATE_HZ;
static constexpr unsigned long kGsrIntervalMs    = 1000UL / GSR_SAMPLE_RATE_HZ;
static constexpr unsigned long kOutputIntervalMs = DEFAULT_OUTPUT_INTERVAL_MS;

static OutputFormat outputFormat = DEFAULT_OUTPUT_FORMAT;

// =============================================================================
// I2C bus scanner & diagnostic health (Hỗ trợ 2 Bus I2C phần cứng riêng biệt)
//   - Bus 0 (Wire) : SDA = GPIO8,  SCL = GPIO9  (Dành cho MAX30102)
//   - Bus 1 (Wire1): SDA = GPIO10, SCL = GPIO11 (Dành cho MPU6050)
// =============================================================================
static void scanI2CBuses() {
  Serial.println(F("\n--- Dò tìm thiết bị I2C Bus 0 (GPIO 8 SDA / GPIO 9 SCL) ---"));
  uint8_t found0 = 0;
  for (uint8_t addr = 1; addr < 127; ++addr) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  [+] Bus 0 tìm thấy địa chỉ 0x%02X", addr);
      if (addr == I2C_ADDR_MAX30102) Serial.print(" -> MAX30102 (PPG / SpO2)");
      Serial.println();
      ++found0;
    }
  }
  Serial.printf("  Tổng cộng Bus 0: %u thiết bị phản hồi\n", found0);

  Serial.println(F("\n--- Dò tìm thiết bị I2C Bus 1 (GPIO 10 SDA / GPIO 11 SCL) ---"));
  uint8_t found1 = 0;
  for (uint8_t addr = 1; addr < 127; ++addr) {
    Wire1.beginTransmission(addr);
    if (Wire1.endTransmission() == 0) {
      Serial.printf("  [+] Bus 1 tìm thấy địa chỉ 0x%02X", addr);
      if (addr == 0x68 || addr == 0x69) Serial.print(" -> MPU-6050 / MPU-6500 (6-DOF IMU)");
      Serial.println();
      ++found1;
    }
  }
  Serial.printf("  Tổng cộng Bus 1: %u thiết bị phản hồi\n", found1);
  Serial.println(F("------------------------------------------------------------\n"));
}

static const char* getBusHealthString() {
  Wire.beginTransmission(I2C_ADDR_MAX30102);
  byte errMax = Wire.endTransmission();
  Wire1.beginTransmission(imuSensor.getAddress());
  byte errImu = Wire1.endTransmission();

  if (errMax == 0 && errImu == 0) return "HOÀN HẢO (Bus 0 [GPIO 8/9] OK | Bus 1 [GPIO 10/11] OK)";
  if (errMax == 0 && errImu != 0) return "CẢNH BÁO (Bus 0: MAX30102 OK | Bus 1: MPU6050 NACK trên GPIO 10/11)";
  if (errMax != 0 && errImu == 0) return "CẢNH BÁO (Bus 0: MAX30102 NACK trên GPIO 8/9 | Bus 1: MPU6050 OK)";
  return "LỖI BUS I2C (Cả 2 bus không phản hồi - Kiểm tra SDA/SCL)";
}

// =============================================================================
// 1. Định dạng văn bản phân tách 3 cảm biến rõ ràng (Formatted Text)
// =============================================================================
static void emitPrettyText(const MAX30102Data& ppg,
                           const MPU6050Data&  imu,
                           const GSRData&      gsr,
                           unsigned long       now) {
  Serial.println(F("\n================================================================================"));
  Serial.printf(" [ASD-EASE SENSOR REPORT] | Uptime: %lu ms | Device: %s\n", now, ASD_DEVICE_ID);
  Serial.printf(" I2C Bus Health: %s\n", getBusHealthString());
  Serial.println(F("--------------------------------------------------------------------------------"));

  // [1] CẢM BIẾN ĐIỆN DA (GSR - EDA)
  Serial.println(F(" [1] CẢM BIẾN ĐIỆN DA (GSR - EDA):"));
  switch (gsr.status) {
    case GSRStatus::DISCONNECTED:
      Serial.println(F("     • Trạng thái          : CHƯA ĐEO ĐIỆN CỰC (Hở mạch - LM324 Low Rail < 150 mV)"));
      Serial.printf("     • Raw ADC (0-4095)    : %u | Điện áp: %u mV (%.3f V)\n",
                    gsr.rawADC, gsr.rawVoltage_mV, gsr.rawVoltage);
      Serial.println(F("     • Độ dẫn da / Trở kháng: Không xác định (Kháng trở hở mạch R -> ∞)"));
      Serial.println(F("     • Session Baseline    : Đang chờ gắn điện cực để kích hoạt baseline 5s"));
      break;

    case GSRStatus::SATURATED:
      Serial.println(F("     • Trạng thái          : BÃO HÒA / NGẮN MẠCH (Điện áp > 3.10V)"));
      Serial.printf("     • Raw ADC (0-4095)    : %u | Điện áp: %u mV (%.3f V)\n",
                    gsr.rawADC, gsr.rawVoltage_mV, gsr.rawVoltage);
      break;

    case GSRStatus::CALIBRATING:
      Serial.println(F("     • Trạng thái          : ĐANG LẤY MẪU BASELINE PHIÊN ĐO (Chờ 5 giây đầu...)"));
      Serial.printf("     • Raw ADC (0-4095)    : %u\n", gsr.rawADC);
      Serial.printf("     • Điện áp (0-3.3 V)   : Raw = %u mV (%.3f V) ──> EMA (α=%.2f) = %u mV (%.3f V)\n",
                    gsr.rawVoltage_mV, gsr.rawVoltage, GSR_EMA_ALPHA_VOLTAGE, gsr.voltage_mV, gsr.voltage);
      Serial.printf("     • Độ dẫn da tạm thời  : Raw = %.2f µS ──> EMA (α=%.2f) = %.2f µS | Trở kháng: %.1f kΩ\n",
                    gsr.rawConductance_uS, GSR_EMA_ALPHA_CONDUCTANCE, gsr.conductance_uS, gsr.resistance / 1000.0f);
      break;

    case GSRStatus::VALID:
      Serial.println(F("     • Trạng thái          : HOẠT ĐỘNG BÌNH THƯỜNG (VALID)"));
      Serial.printf("     • Raw ADC (0-4095)    : %u\n", gsr.rawADC);
      Serial.printf("     • Điện áp (0-3.3 V)   : Raw = %u mV (%.3f V) ──> EMA (α=%.2f) = %u mV (%.3f V)\n",
                    gsr.rawVoltage_mV, gsr.rawVoltage, GSR_EMA_ALPHA_VOLTAGE, gsr.voltage_mV, gsr.voltage);
      Serial.printf("     • Trở kháng da        : %.1f kΩ (%.0f Ω)\n",
                    gsr.resistance / 1000.0f, gsr.resistance);
      Serial.printf("     • Độ dẫn Conductance  : Raw = %.2f µS ──> EMA (α=%.2f) = %.2f µS\n",
                    gsr.rawConductance_uS, GSR_EMA_ALPHA_CONDUCTANCE, gsr.conductance_uS);
      Serial.printf("     • Session Baseline    : %.1f mV | Độ dẫn gốc: %.2f µS\n",
                    gsr.baselineVoltage_mV, gsr.baselineConductance_uS);
      Serial.printf("     • Độ lệch so với gốc  : %+.2f µS (%+.1f %%)\n",
                    gsr.deltaConductance_uS, gsr.percentChange);
      Serial.printf("     • Phản ứng giao cảm   : %s\n",
                    gsr.thresholdExceeded ? ">> PHÁT HIỆN KÍCH THÍCH GIAO CẢM (SCR Event) <<" : "Ổn định sinh lý");
      break;

    default:
      Serial.println(F("     • Trạng thái          : LỖI PHẦN CỨNG ADC"));
      break;
  }

  // [2] CẢM BIẾN TIM MẠCH & SPO2 (MAX30102)
  Serial.println(F("\n [2] CẢM BIẾN TIM MẠCH & SPO2 (MAX30102):"));
  switch (ppg.status) {
    case PPGStatus::NO_FINGER:
      Serial.println(F("     • Trạng thái ngón tay : CHƯA ĐẶT NGÓN TAY (NO_FINGER - IR < 50000)"));
      Serial.printf("     • Tín hiệu quang học  : Raw IR = %lu | Raw RED = %lu\n",
                    static_cast<unsigned long>(ppg.irValue),
                    static_cast<unsigned long>(ppg.redValue));
      Serial.println(F("     • Nhịp tim / SpO2     : Tạm dừng đo (Đang chờ tiếp xúc)"));
      break;

    case PPGStatus::PULSE_ACQUIRING:
      Serial.println(F("     • Trạng thái ngón tay : ĐÃ TIẾP XÚC — ĐANG BẮT XUNG MẠCH (PULSE_ACQUIRING)"));
      Serial.printf("     • Tín hiệu quang học  : Raw IR = %lu | Raw RED = %lu (Biên độ AC: %.1f counts)\n",
                    static_cast<unsigned long>(ppg.irValue),
                    static_cast<unsigned long>(ppg.redValue),
                    ppg.pulseAmplitude);
      if (ppg.medianHeartRate >= HR_MIN_PHYSIOLOGICAL) {
        Serial.printf("     • Nhịp tim tạm tính:\n");
        Serial.printf("       [1] Trung bình trượt (thô)    : %.1f BPM\n", ppg.rawHeartRate);
        Serial.printf("       [2] Trung vị RR (Median)      : %.1f BPM  --> loại nhịp đột biến\n", ppg.medianHeartRate);
        Serial.printf("       [3] EMA nhẹ (a=%.2f) ==> DAU RA: %.1f BPM\n",
                      PPG_EMA_ALPHA_HR, ppg.heartRate);
      } else {
        Serial.println(F("     • Nhịp tim            : Đang chờ bắt đủ 2 đỉnh sóng..."));
      }
      break;

    case PPGStatus::VALID:
      Serial.println(F("     • Trạng thái tín hiệu : TIẾP XÚC TỐT — DỮ LIỆU ỔN ĐỊNH (VALID)"));
      Serial.printf("     • Tín hiệu quang học  : Raw IR = %lu | Raw RED = %lu (Biên độ AC: %.1f counts)\n",
                    static_cast<unsigned long>(ppg.irValue),
                    static_cast<unsigned long>(ppg.redValue),
                    ppg.pulseAmplitude);
      Serial.println(F("     • Nhịp tim (HR) - Pipeline lọc 3 bước:"));
      Serial.printf("       [1] Trung bình trượt (thô)    : %.1f BPM\n", ppg.rawHeartRate);
      Serial.printf("       [2] Trung vị RR (Median)      : %.1f BPM  --> loại nhịp bắt sai/bỏ sót\n", ppg.medianHeartRate);
      Serial.printf("       [3] EMA nhẹ (a=%.2f) ==> DAU RA: %.1f BPM\n",
                    PPG_EMA_ALPHA_HR, ppg.heartRate);
      Serial.println(F("     • SpO2 - Pipeline lọc:"));
      Serial.printf("       [1] Tức thời (thô)            : %.1f %%\n", ppg.rawSpO2);
      Serial.printf("       [2] EMA nhẹ (a=%.2f) ==> DAU RA: %.1f %%  --> làm mượt không biến dạng đỉnh\n",
                    PPG_EMA_ALPHA_SPO2, ppg.spO2);
      Serial.println(F("       [!] SpO2 la gia tri uoc tinh quang hoc, khong dung chan doan y te."));
      break;

    case PPGStatus::DISCONNECTED:
      Serial.println(F("     • Trạng thái          : MẤT KẾT NỐI I2C (Đang tự động thử lại mỗi 3s)"));
      break;

    default:
      Serial.println(F("     • Trạng thái          : LỖI CẢM BIẾN"));
      break;
  }

  // [3] CẢM BIẾN CHUYỂN ĐỘNG (MPU6050 - 6 THÔNG SỐ)
  Serial.println(F("\n [3] CẢM BIẾN CHUYỂN ĐỘNG (MPU6050 - 6 THÔNG SỐ):"));
  if (imu.valid) {
    Serial.printf("     • Trạng thái          : HOẠT ĐỘNG TỐT (VALID) | I2C Bus 1 (SDA: GPIO%d, SCL: GPIO%d)\n",
                  PIN_MPU6050_SDA, PIN_MPU6050_SCL);
    Serial.printf("     • Định danh phần cứng : I2C Addr: 0x%02X | Chip ID (WHO_AM_I): 0x%02X\n",
                  imuSensor.getAddress(), imu.whoAmI);
    Serial.println(F("     • Gia tốc (m/s²):"));
    Serial.printf("       - Raw               : Ax = %7.3f | Ay = %7.3f | Az = %7.3f\n",
                  imu.rawAx, imu.rawAy, imu.rawAz);
    Serial.printf("       - EMA (α=%.2f)       : Ax = %7.3f | Ay = %7.3f | Az = %7.3f (Độ lớn |a|: %7.3f m/s²)\n",
                  IMU_EMA_ALPHA_ACCEL, imu.ax, imu.ay, imu.az, imu.accelMagnitude);
    Serial.println(F("     • Vận tốc góc (°/s):"));
    Serial.printf("       - Raw               : Gx = %7.2f | Gy = %7.2f | Gz = %7.2f\n",
                  imu.rawGx_deg, imu.rawGy_deg, imu.rawGz_deg);
    Serial.printf("       - EMA (α=%.2f)       : Gx = %7.2f | Gy = %7.2f | Gz = %7.2f (rad/s: Gx=%+.3f Gy=%+.3f Gz=%+.3f)\n",
                  IMU_EMA_ALPHA_GYRO, imu.gx_deg, imu.gy_deg, imu.gz_deg, imu.gx, imu.gy, imu.gz);
    Serial.printf("     • Nhiệt độ chip       : %.1f °C\n", imu.temperature);
  } else {
    Serial.println(F("     • Trạng thái          : CHƯA ĐỌC ĐƯỢC / MẤT KẾT NỐI I2C"));
    Serial.printf("     • Cơ chế phục hồi     : Hệ thống đang tự động retry mỗi 3s trên chân SDA=GPIO%d, SCL=GPIO%d\n",
                  PIN_MPU6050_SDA, PIN_MPU6050_SCL);
  }

  Serial.println(F("================================================================================"));
}

// =============================================================================
// 2. Gói dữ liệu JSON thụt dòng đẹp mắt (Pretty JSON)
// =============================================================================
static void emitPrettyJson(const MAX30102Data& ppg,
                           const MPU6050Data&  imu,
                           const GSRData&      gsr,
                           unsigned long       now) {
  JsonDocument doc;

  doc["uptime_ms"] = now;
  doc["device_id"] = ASD_DEVICE_ID;
  doc["bus_health"] = getBusHealthString();

  // 1. GSR (Điện da)
  JsonObject s = doc["gsr_dien_da"].to<JsonObject>();
  s["trang_thai"]            = (gsr.status == GSRStatus::VALID) ? "VALID" :
                               (gsr.status == GSRStatus::CALIBRATING) ? "CALIBRATING" :
                               (gsr.status == GSRStatus::SATURATED) ? "SATURATED" : "DISCONNECTED";
  s["hop_le"]                = gsr.valid;
  s["raw_adc"]               = gsr.rawADC;
  s["dien_ap_raw_mv"]        = gsr.rawVoltage_mV;
  s["dien_ap_raw_v"]         = roundf(gsr.rawVoltage * 1000.0f) / 1000.0f;
  s["dien_ap_ema_mv"]        = gsr.voltage_mV;
  s["dien_ap_ema_v"]         = roundf(gsr.voltage * 1000.0f) / 1000.0f;
  s["ema_alpha_dien_ap"]     = GSR_EMA_ALPHA_VOLTAGE;
  if (gsr.valid) {
    s["tro_khang_ohm"]       = roundf(gsr.resistance);
    s["do_dan_raw_us"]       = roundf(gsr.rawConductance_uS * 100.0f) / 100.0f;
    s["do_dan_ema_us"]       = roundf(gsr.conductance_uS * 100.0f) / 100.0f;
    s["ema_alpha_do_dan"]    = GSR_EMA_ALPHA_CONDUCTANCE;
    s["baseline_mv"]         = roundf(gsr.baselineVoltage_mV * 10.0f) / 10.0f;
    s["baseline_do_dan_us"]  = roundf(gsr.baselineConductance_uS * 100.0f) / 100.0f;
    s["delta_do_dan_us"]     = roundf(gsr.deltaConductance_uS * 100.0f) / 100.0f;
    s["percent_thay_doi"]    = roundf(gsr.percentChange * 10.0f) / 10.0f;
    s["kich_thich_giao_cam"] = gsr.thresholdExceeded;
  }

  // 2. MAX30102 (Tim mạch & SpO2)
  JsonObject p = doc["max30102_tim_spo2"].to<JsonObject>();
  p["trang_thai"]        = (ppg.status == PPGStatus::VALID) ? "VALID" :
                           (ppg.status == PPGStatus::PULSE_ACQUIRING) ? "PULSE_ACQUIRING" :
                           (ppg.status == PPGStatus::NO_FINGER) ? "NO_FINGER" : "DISCONNECTED";
  p["hop_le"]            = ppg.valid;
  p["i2c_bus"]           = 0;
  p["sda_pin"]           = PIN_MAX30102_SDA;
  p["scl_pin"]           = PIN_MAX30102_SCL;
  p["tiep_xuc_tay"]      = ppg.fingerDetected;
  p["ir_raw"]            = ppg.irValue;
  p["red_raw"]           = ppg.redValue;
  p["bien_do_ac"]        = roundf(ppg.pulseAmplitude * 10.0f) / 10.0f;
  if (ppg.fingerDetected) {
    p["nhip_tim_raw_bpm"]    = roundf(ppg.rawHeartRate * 10.0f) / 10.0f;
    p["nhip_tim_median_bpm"] = roundf(ppg.medianHeartRate * 10.0f) / 10.0f;
    p["nhip_tim_ema_bpm"]    = roundf(ppg.heartRate * 10.0f) / 10.0f;
    p["ema_alpha_hr"]        = PPG_EMA_ALPHA_HR;
    p["filter_hr_pipeline"]  = "RollingAvg(raw) -> Median(RR) -> EMA(alpha)";
    p["spo2_raw_percent"]    = roundf(ppg.rawSpO2 * 10.0f) / 10.0f;
    p["spo2_ema_percent"]    = roundf(ppg.spO2 * 10.0f) / 10.0f;
    p["ema_alpha_spo2"]      = PPG_EMA_ALPHA_SPO2;
    p["filter_spo2_pipeline"]= "EMA(alpha_light)";
    p["chu_y_spo2"]          = "Gia tri uoc tinh quang hoc - Khong dung y te";
  }

  // 3. MPU6050 (6 trục)
  JsonObject m = doc["mpu6050_6_truc"].to<JsonObject>();
  m["trang_thai"] = imu.valid ? "VALID" : "DISCONNECTED";
  m["hop_le"]     = imu.valid;
  m["i2c_bus"]    = 1;
  m["sda_pin"]    = PIN_MPU6050_SDA;
  m["scl_pin"]    = PIN_MPU6050_SCL;
  m["i2c_addr"]   = imuSensor.getAddress();
  m["who_am_i"]   = imu.whoAmI;

  if (imu.valid) {
    JsonObject aRaw = m["gia_toc_raw_m_s2"].to<JsonObject>();
    aRaw["ax"] = roundf(imu.rawAx * 1000.0f) / 1000.0f;
    aRaw["ay"] = roundf(imu.rawAy * 1000.0f) / 1000.0f;
    aRaw["az"] = roundf(imu.rawAz * 1000.0f) / 1000.0f;

    JsonObject aEma = m["gia_toc_ema_m_s2"].to<JsonObject>();
    aEma["ax"] = roundf(imu.ax * 1000.0f) / 1000.0f;
    aEma["ay"] = roundf(imu.ay * 1000.0f) / 1000.0f;
    aEma["az"] = roundf(imu.az * 1000.0f) / 1000.0f;
    aEma["do_lon_a"] = roundf(imu.accelMagnitude * 1000.0f) / 1000.0f;
    aEma["alpha"] = IMU_EMA_ALPHA_ACCEL;

    JsonObject gRawDeg = m["con_quay_raw_deg_s"].to<JsonObject>();
    gRawDeg["gx"] = roundf(imu.rawGx_deg * 100.0f) / 100.0f;
    gRawDeg["gy"] = roundf(imu.rawGy_deg * 100.0f) / 100.0f;
    gRawDeg["gz"] = roundf(imu.rawGz_deg * 100.0f) / 100.0f;

    JsonObject gEmaDeg = m["con_quay_ema_deg_s"].to<JsonObject>();
    gEmaDeg["gx"] = roundf(imu.gx_deg * 100.0f) / 100.0f;
    gEmaDeg["gy"] = roundf(imu.gy_deg * 100.0f) / 100.0f;
    gEmaDeg["gz"] = roundf(imu.gz_deg * 100.0f) / 100.0f;
    gEmaDeg["alpha"] = IMU_EMA_ALPHA_GYRO;

    JsonObject gRad = m["con_quay_rad_s"].to<JsonObject>();
    gRad["gx"] = roundf(imu.gx * 1000.0f) / 1000.0f;
    gRad["gy"] = roundf(imu.gy * 1000.0f) / 1000.0f;
    gRad["gz"] = roundf(imu.gz * 1000.0f) / 1000.0f;

    m["nhiet_do_c"] = roundf(imu.temperature * 10.0f) / 10.0f;
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
  delay(1500); // Đợi ổn định cổng USB-CDC

  Serial.println(F("\n========================================================"));
  Serial.println(F("  ASD-EASE Edge Firmware v" FIRMWARE_VERSION));
  Serial.println(F("  Board: ESP32-S3 Super Mini"));
  Serial.println(F("========================================================"));
  Serial.println(F("  Tip: Gõ 'j' để chuyển sang Pretty JSON"));
  Serial.println(F("       Gõ 't' để chuyển sang Formatted Text\n"));

  // ── Khởi tạo 2 Bus I2C phần cứng độc lập ──────────────────────────────────
  // Bus 0 dành cho MAX30102 (SDA=GPIO8, SCL=GPIO9)
  Serial.printf("[I2C0 - MAX30102] Khởi tạo SDA=GPIO%d, SCL=GPIO%d | Tốc độ: %lu kHz\n",
                PIN_MAX30102_SDA, PIN_MAX30102_SCL, I2C_CLOCK_HZ / 1000UL);
  Wire.begin(PIN_MAX30102_SDA, PIN_MAX30102_SCL);
  Wire.setClock(I2C_CLOCK_HZ);
  Wire.setTimeOut(I2C_TIMEOUT_MS);

  // Bus 1 dành riêng cho MPU6050 (SDA=GPIO10, SCL=GPIO11)
  Serial.printf("[I2C1 - MPU6050]  Khởi tạo SDA=GPIO%d, SCL=GPIO%d | Tốc độ: %lu kHz\n",
                PIN_MPU6050_SDA, PIN_MPU6050_SCL, I2C_CLOCK_HZ / 1000UL);
  Wire1.begin(PIN_MPU6050_SDA, PIN_MPU6050_SCL);
  Wire1.setClock(I2C_CLOCK_HZ);
  Wire1.setTimeOut(I2C_TIMEOUT_MS);

  scanI2CBuses();

  // ── Khởi tạo 3 cảm biến độc lập ────────────────────────────────────────────
  Availability s1 = ppgSensor.begin();
  Availability s2 = imuSensor.begin(&Wire1);
  Availability s3 = gsrSensor.begin();

  Serial.printf("\n[STATUS] MAX30102: %s | MPU6050 (0x%02X): %s | GSR: %s\n",
                s1 == Availability::READY ? "READY" : "UNAVAILABLE",
                imuSensor.getAddress(),
                s2 == Availability::READY ? "READY" : "UNAVAILABLE",
                s3 == Availability::READY ? "READY" : "UNAVAILABLE");
  Serial.println(F("[FILTER] Bộ lọc đã kích hoạt:"));
  Serial.printf("  MAX30102 HR  : Trung bình trượt ──► Trung vị RR (Median) ──► EMA nhẹ (α=%.2f)\n", PPG_EMA_ALPHA_HR);
  Serial.printf("  MAX30102 SpO2: EMA nhẹ (α=%.2f)\n", PPG_EMA_ALPHA_SPO2);
  Serial.printf("  MPU6050 Accel: EMA (α=%.2f) + DLPF phần cứng (44 Hz)\n", IMU_EMA_ALPHA_ACCEL);
  Serial.printf("  MPU6050 Gyro : EMA (α=%.2f) + DLPF phần cứng (44 Hz)\n", IMU_EMA_ALPHA_GYRO);
  Serial.printf("  GSR Voltage  : EMA (α=%.2f)\n", GSR_EMA_ALPHA_VOLTAGE);
  Serial.printf("  GSR Conduct  : EMA (α=%.2f)\n\n", GSR_EMA_ALPHA_CONDUCTANCE);

  const unsigned long now = millis();
  lastPpgReadMs = lastImuReadMs = lastGsrReadMs = lastOutputMs = now;
}

// =============================================================================
void loop() {
  const unsigned long now = millis();

  // Xử lý lệnh phím đổi chế độ hiển thị từ Serial Monitor
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == 'j' || c == 'J') {
      outputFormat = OutputFormat::PRETTY_JSON;
      Serial.println(F("\n>>> [Đã đổi chế độ: PRETTY_JSON] <<<"));
    } else if (c == 't' || c == 'T') {
      outputFormat = OutputFormat::PRETTY_TEXT;
      Serial.println(F("\n>>> [Đã đổi chế độ: PRETTY_TEXT] <<<"));
    }
  }

  static MAX30102Data latestPpg;
  static MPU6050Data  latestImu;
  static GSRData      latestGsr;


  if (now - lastPpgReadMs >= kPpgIntervalMs) {
    latestPpg = ppgSensor.read();
    lastPpgReadMs = now;
  }

  if (now - lastImuReadMs >= kImuIntervalMs) {
    latestImu = imuSensor.read();
    lastImuReadMs = now;
  }

  if (now - lastGsrReadMs >= kGsrIntervalMs) {
    latestGsr = gsrSensor.read();
    lastGsrReadMs = now;
  }

  // Xuất gói dữ liệu định kỳ (mặc định 1 Hz = 1000ms)
  if (now - lastOutputMs >= kOutputIntervalMs) {
    emitOutput(latestPpg, latestImu, latestGsr, now);
    lastOutputMs = now;
  }

  // Điều phối nhịp loop chính
  const unsigned long elapsed = millis() - now;
  if (elapsed < LOOP_INTERVAL_MS) {
    delay(LOOP_INTERVAL_MS - elapsed);
  }
}

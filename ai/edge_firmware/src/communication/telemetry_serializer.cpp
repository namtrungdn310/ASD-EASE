// =============================================================================
// telemetry_serializer.cpp — Contract-compliant telemetry JSON builder
// =============================================================================
#include "communication/telemetry_serializer.h"
#include <ArduinoJson.h>
#include "board_config.h"

// ---------------------------------------------------------------------------
// Signal-quality heuristics — engineering estimates, NOT calibrated measures.
// These follow the API contract: 0–1 float, non-nullable.
// ---------------------------------------------------------------------------
static float ppgQuality(const MAX30102Data& ppg) {
  switch (ppg.status) {
    case PPGStatus::VALID:           return 0.9f;
    case PPGStatus::PULSE_ACQUIRING: return 0.5f;
    case PPGStatus::NO_FINGER:       return 0.0f;
    default:                         return 0.0f;
  }
}

static float gsrQuality(const GSRData& gsr) {
  switch (gsr.status) {
    case GSRStatus::VALID:        return 0.9f;
    case GSRStatus::CALIBRATING:  return 0.4f;
    case GSRStatus::SATURATED:    return 0.1f;
    case GSRStatus::DISCONNECTED: return 0.0f;
    default:                      return 0.0f;
  }
}

static float imuQuality(const MPU6050Data& imu) {
  switch (imu.status) {
    case IMUStatus::VALID:       return 1.0f;
    case IMUStatus::CALIBRATING: return 0.4f;
    default:                     return 0.0f;
  }
}

// ---------------------------------------------------------------------------
// Prediction state mapping — no model is deployed, so probability is always
// null and state derives conservatively from sensor readiness.
//   CALIBRATING  — any sensor still calibrating
//   UNCERTAIN    — all sensors initialized but signal quality low / no finger
//   NORMAL       — NOT USED (contract rule: VALID sensors ≠ NORMAL prediction)
//   ATTENTION    — NOT USED without a model
// Without a model we report CALIBRATING or UNCERTAIN only.
// ---------------------------------------------------------------------------
static const char* predictionState(const MAX30102Data& ppg,
                                   const MPU6050Data&  imu,
                                   const GSRData&      gsr) {
  if (ppg.status == PPGStatus::DISCONNECTED ||
      imu.status == IMUStatus::DISCONNECTED ||
      gsr.status == GSRStatus::DISCONNECTED) {
    return "UNCERTAIN";
  }
  if (ppg.status == PPGStatus::PULSE_ACQUIRING ||
      imu.status == IMUStatus::CALIBRATING ||
      gsr.status == GSRStatus::CALIBRATING) {
    return "CALIBRATING";
  }
  // All sensors have data but no model → UNCERTAIN
  return "UNCERTAIN";
}

// ---------------------------------------------------------------------------
String buildTelemetryJson(
    const MAX30102Data& ppg,
    const MPU6050Data&  imu,
    const GSRData&      gsr,
    unsigned long       timestampMs,
    const char*         sessionId)
{
  JsonDocument doc;

  doc["schema_version"] = ASD_SCHEMA_VERSION;
  doc["device_id"]      = ASD_DEVICE_ID;

  if (sessionId != nullptr) {
    doc["session_id"] = sessionId;
  } else {
    doc["session_id"] = (const char*)nullptr;  // JSON null
  }

  doc["timestamp_ms"] = timestampMs;
  doc["data_origin"]  = "DEVICE";

  // hr_bpm — null when unavailable/invalid
  if (ppg.status == PPGStatus::VALID &&
      ppg.heartRate >= HR_MIN_PHYSIOLOGICAL &&
      ppg.heartRate <= HR_MAX_PHYSIOLOGICAL) {
    doc["hr_bpm"] = roundf(ppg.heartRate * 10.0f) / 10.0f;
  } else {
    doc["hr_bpm"] = (const char*)nullptr;
  }

  // gsr
  JsonObject g = doc["gsr"].to<JsonObject>();
  if (gsr.status == GSRStatus::VALID || gsr.status == GSRStatus::CALIBRATING) {
    g["raw"] = gsr.rawADC;
  } else {
    g["raw"] = (const char*)nullptr;
  }
  // delta — null before baseline is established
  if (gsr.status == GSRStatus::VALID && gsr.valid) {
    // Contract: baseline-relative ratio. deltaConductance_uS is absolute
    // difference.  We compute ratio: delta / baseline.  If baseline is near
    // zero we report null to avoid division issues.
    if (gsr.baselineVoltage_mV > 1.0f) {
      float baselineConductance = gsr.conductance_uS -
                                  gsr.deltaConductance_uS;
      if (baselineConductance > 0.01f) {
        g["delta"] = roundf((gsr.deltaConductance_uS / baselineConductance)
                            * 1000.0f) / 1000.0f;
      } else {
        g["delta"] = (const char*)nullptr;
      }
    } else {
      g["delta"] = (const char*)nullptr;
    }
  } else {
    g["delta"] = (const char*)nullptr;
  }

  // movement — null, no algorithm (contract rule)
  JsonObject mv = doc["movement"].to<JsonObject>();
  mv["score"] = (const char*)nullptr;

  // signal_quality
  JsonObject sq = doc["signal_quality"].to<JsonObject>();
  sq["ppg"] = ppgQuality(ppg);
  sq["gsr"] = gsrQuality(gsr);
  sq["imu"] = imuQuality(imu);

  // prediction — no model
  JsonObject pr = doc["prediction"].to<JsonObject>();
  pr["probability"] = (const char*)nullptr;
  pr["state"] = predictionState(ppg, imu, gsr);

  doc["firmware_version"] = ASD_FIRMWARE_VERSION;
  doc["model_version"]    = "none";

  String output;
  serializeJson(doc, output);
  return output;
}

// ---------------------------------------------------------------------------
// Individual sensor serializers for 3 separate MQTT topics
// ---------------------------------------------------------------------------

String buildPpgJson(
    const MAX30102Data& ppg,
    unsigned long       timestampMs,
    const char*         sessionId)
{
  JsonDocument doc;
  doc["schema_version"]   = ASD_SCHEMA_VERSION;
  doc["device_id"]        = ASD_DEVICE_ID;
  if (sessionId != nullptr) {
    doc["session_id"]     = sessionId;
  } else {
    doc["session_id"]     = (const char*)nullptr;
  }
  doc["timestamp_ms"]     = timestampMs;
  doc["data_origin"]      = "DEVICE";
  doc["sensor"]           = "ppg";

  switch (ppg.status) {
    case PPGStatus::VALID:           doc["status"] = "VALID"; break;
    case PPGStatus::PULSE_ACQUIRING: doc["status"] = "PULSE_ACQUIRING"; break;
    case PPGStatus::NO_FINGER:       doc["status"] = "NO_FINGER"; break;
    case PPGStatus::DISCONNECTED:    doc["status"] = "DISCONNECTED"; break;
    default:                         doc["status"] = "ERROR"; break;
  }

  if (ppg.status == PPGStatus::VALID &&
      ppg.heartRate >= HR_MIN_PHYSIOLOGICAL &&
      ppg.heartRate <= HR_MAX_PHYSIOLOGICAL) {
    doc["hr_bpm"] = roundf(ppg.heartRate * 10.0f) / 10.0f;
  } else {
    doc["hr_bpm"] = (const char*)nullptr;
  }

  if (ppg.status == PPGStatus::VALID && ppg.spO2 > 0.0f) {
    doc["spo2"] = roundf(ppg.spO2 * 10.0f) / 10.0f;
  } else {
    doc["spo2"] = (const char*)nullptr;
  }

  doc["ir"]               = ppg.irValue;
  doc["red"]              = ppg.redValue;
  doc["signal_quality"]   = ppgQuality(ppg);
  doc["firmware_version"] = ASD_FIRMWARE_VERSION;

  String output;
  serializeJson(doc, output);
  return output;
}

String buildGsrJson(
    const GSRData&      gsr,
    unsigned long       timestampMs,
    const char*         sessionId)
{
  JsonDocument doc;
  doc["schema_version"]   = ASD_SCHEMA_VERSION;
  doc["device_id"]        = ASD_DEVICE_ID;
  if (sessionId != nullptr) {
    doc["session_id"]     = sessionId;
  } else {
    doc["session_id"]     = (const char*)nullptr;
  }
  doc["timestamp_ms"]     = timestampMs;
  doc["data_origin"]      = "DEVICE";
  doc["sensor"]           = "gsr";

  switch (gsr.status) {
    case GSRStatus::VALID:        doc["status"] = "VALID"; break;
    case GSRStatus::CALIBRATING:  doc["status"] = "CALIBRATING"; break;
    case GSRStatus::SATURATED:    doc["status"] = "SATURATED"; break;
    case GSRStatus::DISCONNECTED: doc["status"] = "DISCONNECTED"; break;
    default:                      doc["status"] = "ERROR"; break;
  }

  if (gsr.status == GSRStatus::VALID || gsr.status == GSRStatus::CALIBRATING) {
    doc["raw"] = gsr.rawADC;
  } else {
    doc["raw"] = (const char*)nullptr;
  }

  if (gsr.status == GSRStatus::VALID && gsr.valid && gsr.baselineVoltage_mV > 1.0f) {
    float baselineConductance = gsr.conductance_uS - gsr.deltaConductance_uS;
    if (baselineConductance > 0.01f) {
      doc["delta"] = roundf((gsr.deltaConductance_uS / baselineConductance) * 1000.0f) / 1000.0f;
    } else {
      doc["delta"] = (const char*)nullptr;
    }
  } else {
    doc["delta"] = (const char*)nullptr;
  }

  doc["voltage_mv"]       = gsr.voltage_mV;
  doc["conductance_us"]   = roundf(gsr.conductance_uS * 100.0f) / 100.0f;
  doc["signal_quality"]   = gsrQuality(gsr);
  doc["firmware_version"] = ASD_FIRMWARE_VERSION;

  String output;
  serializeJson(doc, output);
  return output;
}

String buildImuJson(
    const MPU6050Data&  imu,
    unsigned long       timestampMs,
    const char*         sessionId)
{
  JsonDocument doc;
  doc["schema_version"]   = ASD_SCHEMA_VERSION;
  doc["device_id"]        = ASD_DEVICE_ID;
  if (sessionId != nullptr) {
    doc["session_id"]     = sessionId;
  } else {
    doc["session_id"]     = (const char*)nullptr;
  }
  doc["timestamp_ms"]     = timestampMs;
  doc["data_origin"]      = "DEVICE";
  doc["sensor"]           = "imu";

  switch (imu.status) {
    case IMUStatus::VALID:        doc["status"] = "VALID"; break;
    case IMUStatus::CALIBRATING:  doc["status"] = "CALIBRATING"; break;
    case IMUStatus::DISCONNECTED: doc["status"] = "DISCONNECTED"; break;
    default:                      doc["status"] = "ERROR"; break;
  }

  JsonObject accel = doc["accel"].to<JsonObject>();
  accel["x"] = roundf(imu.ax * 100.0f) / 100.0f;
  accel["y"] = roundf(imu.ay * 100.0f) / 100.0f;
  accel["z"] = roundf(imu.az * 100.0f) / 100.0f;

  JsonObject gyro = doc["gyro"].to<JsonObject>();
  gyro["x"] = roundf(imu.gx * 100.0f) / 100.0f;
  gyro["y"] = roundf(imu.gy * 100.0f) / 100.0f;
  gyro["z"] = roundf(imu.gz * 100.0f) / 100.0f;

  doc["movement_score"]   = (const char*)nullptr;
  doc["temperature"]      = roundf(imu.temperature * 10.0f) / 10.0f;
  doc["signal_quality"]   = imuQuality(imu);
  doc["firmware_version"] = ASD_FIRMWARE_VERSION;

  String output;
  serializeJson(doc, output);
  return output;
}


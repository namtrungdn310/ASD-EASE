#pragma once
// =============================================================================
// telemetry_serializer.h — Build API-contract JSON from sensor snapshots
// =============================================================================
// Produces a JSON string that matches the Pydantic Telemetry schema v1.0.
// This is NOT the Serial debug JSON — it is the wire payload for MQTT/HTTP.
// =============================================================================

#include <Arduino.h>
#include "board_config.h"
#include "MAX30102Sensor.h"
#include "MPU6050Sensor.h"
#include "GSRSensor.h"

/// Serialize a telemetry snapshot into a compact JSON string that the backend
/// Pydantic Telemetry model will accept.
///
/// Rules derived from API_CONTRACT.md / doc 03:
///  - hr_bpm:  null when PPG status != VALID or heart rate < HR_MIN
///  - gsr.raw: ADC count (after 8x averaging); null when GSR disconnected/error
///  - gsr.delta: null when baseline not established (CALIBRATING/DISCONNECTED)
///  - movement.score: null — no algorithm yet (contract rule)
///  - signal_quality.*: engineering heuristic 0–1
///  - prediction.*: probability null, state from sensor status mapping,
///    model_version "none" (no edge model deployed)
///
/// The caller is responsible for taking a consistent snapshot of the three
/// sensor data structs (copy, not pointer) before calling this function.
String buildTelemetryJson(
    const MAX30102Data& ppg,
    const MPU6050Data&  imu,
    const GSRData&      gsr,
    unsigned long       timestampMs,
    const char*         sessionId   // nullptr when no active session
);

/// Serialize PPG (MAX30102) sensor data for topic:
/// asd/v1/devices/{deviceId}/sensors/ppg
String buildPpgJson(
    const MAX30102Data& ppg,
    unsigned long       timestampMs,
    const char*         sessionId
);

/// Serialize GSR sensor data for topic:
/// asd/v1/devices/{deviceId}/sensors/gsr
String buildGsrJson(
    const GSRData&      gsr,
    unsigned long       timestampMs,
    const char*         sessionId
);

/// Serialize IMU (MPU6050) sensor data for topic:
/// asd/v1/devices/{deviceId}/sensors/imu
String buildImuJson(
    const MPU6050Data&  imu,
    unsigned long       timestampMs,
    const char*         sessionId
);


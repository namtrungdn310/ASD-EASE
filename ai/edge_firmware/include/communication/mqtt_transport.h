#pragma once
#include <Arduino.h>
#include "communication/session_protocol.h"

struct SensorTelemetry {
  float hr_bpm = 0.0f;
  float spo2_pct = 0.0f;
  bool finger = false;
  bool ppg_valid = false;
  char ppg_status[16] = "NO_FINGER";

  float ax = 0.0f, ay = 0.0f, az = 0.0f, accel_mag = 0.0f;
  float gx_deg = 0.0f, gy_deg = 0.0f, gz_deg = 0.0f;
  float temp_c = 0.0f;
  bool imu_valid = false;
  char imu_status[16] = "DISCONNECTED";

  float voltage_v = 0.0f;
  uint32_t voltage_mv = 0;
  float resistance_kohm = 0.0f;
  float conductance_us = 0.0f;
  uint16_t raw_adc = 0;
  bool gsr_valid = false;
  char gsr_status[16] = "DISCONNECTED";
};

struct MqttStats {
  uint32_t publishOk = 0, publishFail = 0, dropped = 0, reconnects = 0;
  uint32_t invalid = 0, sensingLoops = 0, maxLoopGapMs = 0;
  uint32_t minHeapBytes = 0, networkStackHighWater = 0;
  uint32_t controlDropped = 0, pendingControl = 0, outboxBytes = 0;
  int transportError = 0, fatalReason = 0;
  uint32_t ppgSamples = 0, imuSamples = 0, gsrSamples = 0;
  bool wifiConnected = false, mqttConnected = false, synchronized = false;
};

bool mqttTransportSetup();
// Chỉ ghi queue length1, không gọi Wi-Fi/MQTT/serialize trong task sensing.
void mqttUpdateSnapshot(const asd::ReadingSnapshot& snapshot);
void mqttUpdateSensors(const SensorTelemetry& sensors);
void mqttRecordSensing(uint32_t now, uint32_t ppgSamples, bool imuNew, bool gsrNew);
MqttStats mqttGetStats();

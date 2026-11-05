#pragma once
#include <Arduino.h>
#include "communication/session_protocol.h"

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
void mqttRecordSensing(uint32_t now, uint32_t ppgSamples, bool imuNew, bool gsrNew);
MqttStats mqttGetStats();

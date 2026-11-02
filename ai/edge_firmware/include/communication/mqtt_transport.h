#pragma once
// =============================================================================
// mqtt_transport.h — MQTT telemetry publisher for ASD-EASE
// =============================================================================
// Publishes telemetry JSON to the MQTT broker in a non-blocking fashion.
// Wi-Fi and MQTT reconnect run with finite timeouts so sensing is never
// blocked.  All credentials come from network_config.h (gitignored).
// =============================================================================

#include <Arduino.h>

// Check for local config — build still compiles without it (networking disabled)
#if __has_include("network_config.h")
  #include "network_config.h"
  #define ASD_NETWORK_CONFIGURED 1
#else
  #define ASD_NETWORK_CONFIGURED 0
  #ifndef WIFI_SSID
    #define WIFI_SSID ""
  #endif
  #ifndef WIFI_PASSWORD
    #define WIFI_PASSWORD ""
  #endif
  #ifndef MQTT_BROKER_HOST
    #define MQTT_BROKER_HOST ""
  #endif
  #ifndef MQTT_BROKER_PORT
    #define MQTT_BROKER_PORT 1883
  #endif
  #ifndef MQTT_USERNAME
    #define MQTT_USERNAME ""
  #endif
  #ifndef MQTT_PASSWORD
    #define MQTT_PASSWORD ""
  #endif
#endif

// =============================================================================
// Statistics (read-only from outside)
// =============================================================================
struct MqttStats {
  uint32_t publishOk   = 0;
  uint32_t publishFail = 0;
  uint32_t dropped     = 0;   // messages dropped because queue was full
  uint32_t reconnects  = 0;
  bool     wifiConnected = false;
  bool     mqttConnected = false;
};

// =============================================================================
// Public API
// =============================================================================

/// Call once in setup(). Returns true if networking is configured.
bool mqttTransportSetup();

/// Call periodically (e.g. every loop iteration) to service Wi-Fi/MQTT
/// reconnects and flush the outbound queue.  Never blocks longer than a few
/// hundred milliseconds.
void mqttTransportLoop();

/// Enqueue a telemetry JSON payload for publishing.  Returns false if the
/// queue is full (caller should count as a drop).
bool mqttEnqueueTelemetry(const String& jsonPayload, const char* deviceId);

/// Enqueue a sensor-specific JSON payload for publishing to:
/// asd/v1/devices/{deviceId}/sensors/{sensorType}
bool mqttEnqueueSensor(const String& jsonPayload, const char* deviceId, const char* sensorType);

/// Read-only access to counters.
const MqttStats& mqttGetStats();


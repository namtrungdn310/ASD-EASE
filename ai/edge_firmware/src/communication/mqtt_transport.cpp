// =============================================================================
// mqtt_transport.cpp — Non-blocking MQTT publish with queue & reconnect
// =============================================================================
#include "communication/mqtt_transport.h"

#if ASD_NETWORK_CONFIGURED

#include <WiFi.h>
#include <PubSubClient.h>
#include "board_config.h"

// ---------------------------------------------------------------------------
// Outbound queue — ring buffer with bounded capacity
// ---------------------------------------------------------------------------
static constexpr size_t QUEUE_CAPACITY = 16;

struct QueueItem {
  String payload;
  String topic;
  bool   occupied = false;
};

static QueueItem  _queue[QUEUE_CAPACITY];
static size_t     _queueHead = 0;
static size_t     _queueTail = 0;
static size_t     _queueCount = 0;

static MqttStats  _stats;

// ---------------------------------------------------------------------------
// Networking objects
// ---------------------------------------------------------------------------
static WiFiClient    _wifiClient;
static PubSubClient  _mqttClient(_wifiClient);

// Reconnect backoff
static unsigned long _lastWifiAttemptMs = 0;
static unsigned long _lastMqttAttemptMs = 0;
static unsigned long _wifiBackoffMs = 2000;
static unsigned long _mqttBackoffMs = 2000;

static constexpr unsigned long WIFI_CONNECT_TIMEOUT_MS = 8000;
static constexpr unsigned long BACKOFF_MAX_MS          = 30000;

// ---------------------------------------------------------------------------
// Wi-Fi management (non-blocking)
// ---------------------------------------------------------------------------
static bool ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    _stats.wifiConnected = true;
    _wifiBackoffMs = 2000;
    return true;
  }

  _stats.wifiConnected = false;

  unsigned long now = millis();
  if (now - _lastWifiAttemptMs < _wifiBackoffMs) {
    return false;
  }
  _lastWifiAttemptMs = now;

  Serial.printf("[MQTT] Wi-Fi connecting to %s …\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Wait with a finite timeout — never block indefinitely.
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED &&
         (millis() - start) < WIFI_CONNECT_TIMEOUT_MS) {
    delay(100);
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[MQTT] Wi-Fi connected — IP %s\n",
                  WiFi.localIP().toString().c_str());
    _stats.wifiConnected = true;
    _wifiBackoffMs = 2000;
    return true;
  }

  Serial.printf("[MQTT] Wi-Fi connect failed, retry in %lu ms\n", _wifiBackoffMs);
  _wifiBackoffMs = min(_wifiBackoffMs * 2, BACKOFF_MAX_MS);
  return false;
}

// ---------------------------------------------------------------------------
// MQTT connection management (non-blocking)
// ---------------------------------------------------------------------------
static bool ensureMqtt() {
  if (_mqttClient.connected()) {
    _stats.mqttConnected = true;
    _mqttBackoffMs = 2000;
    return true;
  }

  _stats.mqttConnected = false;

  unsigned long now = millis();
  if (now - _lastMqttAttemptMs < _mqttBackoffMs) {
    return false;
  }
  _lastMqttAttemptMs = now;

  Serial.printf("[MQTT] Connecting to broker %s:%d …\n",
                MQTT_BROKER_HOST, MQTT_BROKER_PORT);

  _mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);

  // Unique client ID per boot
  String clientId = "asd-esp32-";
  clientId += String(random(0xFFFF), HEX);

  if (_mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
    Serial.println("[MQTT] Connected to broker");
    _stats.mqttConnected = true;
    _stats.reconnects++;
    _mqttBackoffMs = 2000;
    return true;
  }

  Serial.printf("[MQTT] Broker connect failed (rc=%d), retry in %lu ms\n",
                _mqttClient.state(), _mqttBackoffMs);
  _mqttBackoffMs = min(_mqttBackoffMs * 2, BACKOFF_MAX_MS);
  return false;
}

// ---------------------------------------------------------------------------
// Queue helpers
// ---------------------------------------------------------------------------
static bool queuePush(const String& payload, const String& topic) {
  if (_queueCount >= QUEUE_CAPACITY) {
    return false;
  }
  _queue[_queueTail].payload  = payload;
  _queue[_queueTail].topic    = topic;
  _queue[_queueTail].occupied = true;
  _queueTail = (_queueTail + 1) % QUEUE_CAPACITY;
  _queueCount++;
  return true;
}

static bool queuePop(String& payload, String& topic) {
  if (_queueCount == 0) {
    return false;
  }
  payload = _queue[_queueHead].payload;
  topic   = _queue[_queueHead].topic;
  _queue[_queueHead].payload  = String();  // release memory
  _queue[_queueHead].topic    = String();
  _queue[_queueHead].occupied = false;
  _queueHead = (_queueHead + 1) % QUEUE_CAPACITY;
  _queueCount--;
  return true;
}

static void flushQueue() {
  String payload, topic;
  while (_mqttClient.connected() && queuePop(payload, topic)) {
    bool ok = _mqttClient.publish(topic.c_str(),
                                  payload.c_str(),
                                  false /* retain */);
    if (ok) {
      _stats.publishOk++;
    } else {
      _stats.publishFail++;
      Serial.printf("[MQTT] Publish failed on %s (len=%u)\n",
                    topic.c_str(), payload.length());
    }
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

bool mqttTransportSetup() {
  Serial.println("[MQTT] Transport enabled (network_config.h found)");
  _mqttClient.setBufferSize(1024);  // telemetry JSON is ~400–600 bytes
  return true;
}

void mqttTransportLoop() {
  if (!ensureWifi()) return;
  if (!ensureMqtt()) return;

  _mqttClient.loop();  // service keepalive / incoming
  flushQueue();
}

bool mqttEnqueueTelemetry(const String& jsonPayload, const char* deviceId) {
  String topic = "asd/v1/devices/";
  topic += deviceId;
  topic += "/telemetry";

  if (!queuePush(jsonPayload, topic)) {
    _stats.dropped++;
    return false;
  }
  return true;
}

bool mqttEnqueueSensor(const String& jsonPayload, const char* deviceId, const char* sensorType) {
  String topic = "asd/v1/devices/";
  topic += deviceId;
  topic += "/sensors/";
  topic += sensorType;

  if (!queuePush(jsonPayload, topic)) {
    _stats.dropped++;
    return false;
  }
  return true;
}

const MqttStats& mqttGetStats() {
  return _stats;
}

#else
// ----------------------------------------------------------------------------
static MqttStats _stubStats;

bool mqttTransportSetup() {
  Serial.println("[MQTT] Transport DISABLED — no network_config.h");
  return false;
}

void mqttTransportLoop() {}

bool mqttEnqueueTelemetry(const String&, const char*) {
  return false;
}

bool mqttEnqueueSensor(const String&, const char*, const char*) {
  return false;
}

const MqttStats& mqttGetStats() {
  return _stubStats;
}

#endif 

#include "communication/mqtt_transport.h"
#include "communication/network_settings.h"
#include "board_config.h"
#include <WiFi.h>
#include <mqtt_client.h>
#include <esp_timer.h>
#include <esp_system.h>
#include <esp_heap_caps.h>
#include <atomic>
#include <array>

namespace {
portMUX_TYPE statsMux = portMUX_INITIALIZER_UNLOCKED;
MqttStats stats;
QueueHandle_t snapshotQueue = nullptr, inbox = nullptr, published = nullptr, subscribed = nullptr;
TaskHandle_t worker = nullptr;
esp_mqtt_client_handle_t client = nullptr;
std::atomic<bool> connected{false}, connectionFailed{false};
std::atomic<int> fatalReason{0}, lastTransportError{0};
std::string prefix, presenceTopic, will, clientId;
struct Packet { char suffix[24]; char payload[4097]; bool retained; };
struct Flight { int id = 0; uint64_t at = 0; };
std::array<Flight, 8> flights;
size_t flightCount = 0;
uint32_t previousLoop = 0;
bool haveLoop = false;

uint64_t clockMs() { return static_cast<uint64_t>(esp_timer_get_time()) / 1000; }
std::string randomId() {
  char output[33];
  snprintf(output, sizeof(output), "%08lx%08lx%08lx%08lx",
    static_cast<unsigned long>(esp_random()), static_cast<unsigned long>(esp_random()),
    static_cast<unsigned long>(esp_random()), static_cast<unsigned long>(esp_random()));
  return output;
}
void countDrop() { portENTER_CRITICAL(&statsMux); ++stats.dropped; portEXIT_CRITICAL(&statsMux); }

void event(void*, esp_event_base_t, int32_t type, void* pointer) {
  auto e = static_cast<esp_mqtt_event_handle_t>(pointer);
  if (!e || e->client != client) return;
  if (type == MQTT_EVENT_CONNECTED) connected = true;
  else if (type == MQTT_EVENT_DISCONNECTED) connectionFailed = true;
  else if (type == MQTT_EVENT_ERROR) {
    connectionFailed = true;
    if (e->error_handle) {
      auto error = e->error_handle;
      lastTransportError = error->error_type == MQTT_ERROR_TYPE_CONNECTION_REFUSED ?
        static_cast<int>(error->connect_return_code) : error->esp_tls_last_esp_err;
      if (error->error_type == MQTT_ERROR_TYPE_CONNECTION_REFUSED &&
          error->connect_return_code != MQTT_CONNECTION_REFUSE_SERVER_UNAVAILABLE)
        fatalReason = static_cast<int>(error->connect_return_code);
      if (error->esp_tls_cert_verify_flags) fatalReason = -1;
    }
  }
  else if (type == MQTT_EVENT_PUBLISHED) {
    if (xQueueSend(published, &e->msg_id, 0) != pdTRUE) connectionFailed = true;
  } else if (type == MQTT_EVENT_SUBSCRIBED) {
    for (int i = 0; i < e->data_len; ++i)
      if (static_cast<unsigned char>(e->data[i]) == 0x80) { fatalReason = -2; connectionFailed = true; return; }
    if (xQueueSend(subscribed, &e->msg_id, 0) != pdTRUE) connectionFailed = true;
  } else if (type == MQTT_EVENT_DATA) {
    // Buffer4608 nhận trọn gói4096; không cấp phát/gom fragment trong callback.
    if (e->current_data_offset != 0 || e->data_len != e->total_data_len ||
        e->data_len <= 0 || e->data_len > 4096 || e->topic_len <= 0 ||
        e->topic_len > 256 || e->qos != 1 || e->retain) { countDrop(); return; }
    Packet packet{};
    std::string topic(e->topic, e->topic_len);
    if (topic == prefix + "command") strcpy(packet.suffix, "command");
    else if (topic == prefix + "state/response") strcpy(packet.suffix, "state/response");
    else { countDrop(); return; }
    memcpy(packet.payload, e->data, e->data_len);
    packet.payload[e->data_len] = 0;
    if (memchr(e->data, 0, e->data_len) || xQueueSend(inbox, &packet, 0) != pdTRUE) countDrop();
  }
}

uint32_t retryDelay(uint32_t base) { return base + esp_random() % (base / 5 + 1); }
bool validConfig() {
#ifdef ASD_NETWORK_BUILD_CHECK
  // Volatile giữ cả nhánh mạng để linker kiểm tra SDK; fixture không tự kết nối khi nạp nhầm.
  static volatile bool compileOnly = true;
  if (compileOnly) return false;
#endif
  return ASD_NETWORK_ENABLED && strlen(WIFI_SSID) && strlen(MQTT_BROKER_HOST) &&
    strlen(MQTT_USERNAME) && strlen(MQTT_PASSWORD) && asd::validId(MQTT_DEVICE_ID) &&
    strcmp(MQTT_BROKER_HOST, "localhost") != 0 && strcmp(MQTT_BROKER_HOST, "127.0.0.1") != 0 &&
    ((MQTT_USE_TLS && strlen(MQTT_CA_CERT)) || (!MQTT_USE_TLS && ASD_ALLOW_INSECURE_LAN));
}
void closeClient(asd::SessionProtocol& protocol) {
  connected = false;
  protocol.disconnected();
  if (client) {
    esp_mqtt_client_stop(client);
    esp_mqtt_client_destroy(client);
    client = nullptr;
  }
  xQueueReset(inbox); xQueueReset(published); xQueueReset(subscribed);
  for (auto& flight : flights) flight = {};
  flightCount = 0;
}
bool openClient(asd::SessionProtocol& protocol, uint64_t now) {
  const std::string connection = randomId();
  protocol.connected(connection, now);
  Serial.printf("[MQTT] CONNECT connection=%s\n", connection.c_str());
  will = protocol.presence(false);
  esp_mqtt_client_config_t config{};
  config.host = MQTT_BROKER_HOST; config.port = MQTT_BROKER_PORT;
  config.username = MQTT_USERNAME; config.password = MQTT_PASSWORD;
  config.client_id = clientId.c_str();
  config.lwt_topic = presenceTopic.c_str(); config.lwt_msg = will.c_str();
  config.lwt_msg_len = will.size(); config.lwt_qos = 1; config.lwt_retain = 1;
  config.keepalive = 15; config.disable_clean_session = false;
  config.disable_auto_reconnect = true; config.network_timeout_ms = 3000;
  config.buffer_size = 4608; config.out_buffer_size = 4608;
  config.task_stack = 6144; config.task_prio = 1;
  config.protocol_ver = MQTT_PROTOCOL_V_3_1_1;
  config.transport = MQTT_USE_TLS ? MQTT_TRANSPORT_OVER_SSL : MQTT_TRANSPORT_OVER_TCP;
  config.cert_pem = MQTT_USE_TLS ? MQTT_CA_CERT : nullptr;
  config.skip_cert_common_name_check = false;
  connectionFailed = false;
  client = esp_mqtt_client_init(&config);
  if (!client) return false;
  esp_mqtt_client_register_event(client, MQTT_EVENT_ANY, event, nullptr);
  return esp_mqtt_client_start(client) == ESP_OK;
}
bool send(asd::Outbound& output, uint64_t now) {
  const std::string topic = prefix + output.suffix;
  if (!connected || topic.size() > 256 || output.payload.size() > 4096) return false;
  if (output.qos == 0) {
    // Có thể chờ tối đa network timeout, nhưng chỉ ở worker mạng, không task sensing.
    return esp_mqtt_client_publish(client, topic.c_str(), output.payload.c_str(), output.payload.size(), 0, false) >= 0;
  }
  if (flightCount >= flights.size() || esp_mqtt_client_get_outbox_size(client) + output.payload.size() + topic.size() + 16 > 32768) return false;
  int id = esp_mqtt_client_enqueue(client, topic.c_str(), output.payload.c_str(), output.payload.size(), 1, output.retain, true);
  if (id < 0) return false;
  for (auto& flight : flights) if (!flight.id) { flight = {id, now}; ++flightCount; break; }
  return true;
}

void networkTask(void*) {
  const std::string boot = randomId();
  asd::SessionProtocol protocol(MQTT_DEVICE_ID, "DEVICE", ASD_FIRMWARE_VERSION,
    boot, {PPG_EFFECTIVE_RATE_HZ, IMU_SAMPLE_RATE_HZ, GSR_SAMPLE_RATE_HZ}, randomId);
  Serial.printf("[MQTT] boot=%s firmware=%s\n", boot.c_str(), ASD_FIRMWARE_VERSION);
  prefix = std::string("asd-ease/v1/DEVICE/") + MQTT_DEVICE_ID + "/";
  presenceTopic = prefix + "presence";
  clientId = std::string("asd-") + randomId().substr(0, 24);
  uint32_t wifiBackoff = 1000, mqttBackoff = 1000;
  uint64_t wifiNext = 0, mqttNext = 0, connectingAt = 0, wifiAttemptAt = 0;
  uint64_t nextTelemetry = 0, lastMetrics = 0;
  uint64_t loggedGeneration = 0, lastErrorLog = 0;
  std::string loggedState = "IDLE", loggedError;
  bool wifiAttempt = false, ready = false, subscribedOnce = false;
  int loggedFatal = 0;
  int subscribeIds[2] = {-1,-1};
  bool subAck[2] = {false,false};
  asd::ReadingSnapshot snapshot{};
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);
  for (;;) {
    uint64_t now = clockMs();
    bool wifi = WiFi.status() == WL_CONNECTED;
    if (!wifi) {
      if (client) closeClient(protocol);
      ready = subscribedOnce = false;
      if (wifiAttempt && now - wifiAttemptAt >= 3000) {
        WiFi.disconnect();
        wifiAttempt = false;
        wifiNext = now + retryDelay(wifiBackoff);
        wifiBackoff = std::min<uint32_t>(30000, wifiBackoff * 2);
      }
      if (!wifiAttempt && now >= wifiNext) {
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        wifiAttemptAt = now; wifiAttempt = true;
      }
    } else {
      wifiAttempt = false; wifiBackoff = 1000;
      if (client && (connectionFailed || (!connected && now - connectingAt >= 6000))) {
        closeClient(protocol);
        ready = subscribedOnce = false;
        mqttNext = now + retryDelay(mqttBackoff);
        mqttBackoff = std::min<uint32_t>(30000, mqttBackoff * 2);
      }
      if (client && connected && !ready && now - connectingAt >= 6000) connectionFailed = true;
      if (!client && !fatalReason && now >= mqttNext) {
        connectingAt = now;
        if (!openClient(protocol, now)) {
          connectionFailed = true;
          mqttNext = now + retryDelay(mqttBackoff);
          mqttBackoff = std::min<uint32_t>(30000, mqttBackoff * 2);
        }
      }
      if (client && connected && !subscribedOnce) {
        subscribeIds[0] = esp_mqtt_client_subscribe(client, (prefix + "command").c_str(), 1);
        subscribeIds[1] = esp_mqtt_client_subscribe(client, (prefix + "state/response").c_str(), 1);
        subAck[0] = subAck[1] = false;
        subscribedOnce = true;
        if (subscribeIds[0] < 0 || subscribeIds[1] < 0) connectionFailed = true;
      }
      int id = 0;
      while (xQueueReceive(subscribed, &id, 0) == pdTRUE)
        for (int i=0; i<2; ++i) if (subscribeIds[i] == id) subAck[i] = true;
      if (subscribedOnce && !ready && subAck[0] && subAck[1]) {
        ready = true;
        // Core connected() đã tạo nonce trước CONNECT. Tick chỉ sau cả hai SUBACK.
        asd::Outbound online{"presence", protocol.presence(true), 1, true};
        if (!send(online, now)) connectionFailed = true;
        mqttBackoff = 1000;
        portENTER_CRITICAL(&statsMux); ++stats.reconnects; portEXIT_CRITICAL(&statsMux);
      }
      while (xQueueReceive(published, &id, 0) == pdTRUE)
        for (auto& flight : flights) if (flight.id == id) { flight = {}; --flightCount; break; }
      for (const auto& flight : flights) if (flight.id && now - flight.at > 30000) connectionFailed = true;
      if (ready && !connectionFailed) {
        protocol.transportPending(flightCount, esp_mqtt_client_get_outbox_size(client));
        Packet packet;
        for (int i=0; i<8 && xQueueReceive(inbox, &packet, 0) == pdTRUE; ++i)
          protocol.receive(packet.suffix, packet.payload, packet.retained, now);
        protocol.tick(now);
        if (protocol.generation() != loggedGeneration || protocol.state() != loggedState) {
          loggedGeneration = protocol.generation(); loggedState = protocol.state();
          Serial.printf("[CONTROL] generation=%llu state=%s session=%s timestamp=%llu\n",
            static_cast<unsigned long long>(loggedGeneration), loggedState.c_str(), protocol.session().c_str(),
            static_cast<unsigned long long>(now));
        }
        if (!protocol.lastError().empty() && protocol.lastError() != loggedError && now - lastErrorLog >= 1000) {
          loggedError = protocol.lastError(); lastErrorLog = now;
          Serial.printf("[CONTROL] reject=%s\n", loggedError.c_str());
        }
        asd::Outbound output;
        while (flightCount < flights.size() && protocol.pop(output)) {
          bool ok = send(output, now);
          portENTER_CRITICAL(&statsMux);
          if (ok) ++stats.publishOk; else ++stats.publishFail;
          portEXIT_CRITICAL(&statsMux);
          if (!ok) { connectionFailed = true; break; }
        }
        if (now >= nextTelemetry) {
          // Queue length1 luôn lấy snapshot mới nhất, không xả backlog.
          if (xQueueReceive(snapshotQueue, &snapshot, 0) == pdTRUE && protocol.telemetry(snapshot, now, output)) {
            bool ok = send(output, now);
            portENTER_CRITICAL(&statsMux);
            if (ok) ++stats.publishOk; else ++stats.publishFail;
            portEXIT_CRITICAL(&statsMux);
          }
          nextTelemetry = now + 1000;
        }
      }
    }
    if (now - lastMetrics >= 5000) {
      auto heap = esp_get_minimum_free_heap_size();
      auto stack = uxTaskGetStackHighWaterMark(nullptr);
      auto outbox = client ? esp_mqtt_client_get_outbox_size(client) : 0;
      portENTER_CRITICAL(&statsMux);
      stats.wifiConnected = wifi; stats.mqttConnected = connected;
      stats.synchronized = protocol.authorized(now);
      stats.invalid = protocol.rejected();
      stats.controlDropped = protocol.dropped();
      stats.pendingControl = flightCount;
      stats.outboxBytes = outbox;
      stats.transportError = lastTransportError;
      stats.fatalReason = fatalReason;
      stats.minHeapBytes = heap;
      stats.networkStackHighWater = stack;
      portEXIT_CRITICAL(&statsMux);
      lastMetrics = now;
    }
    if (fatalReason && loggedFatal != fatalReason) {
      loggedFatal = fatalReason;
      Serial.printf("[MQTT] Dung retry loi cau hinh/quyen/chung chi (%d); sua cau hinh roi reboot.\n", loggedFatal);
    }
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}
} // namespace

bool mqttTransportSetup() {
  if (!validConfig()) {
    Serial.println("[MQTT] Tat mang: thieu cau hinh/opt-in/TLS hoac chi build-check.");
    return false;
  }
  Serial.printf("[MQTT] device=%s transport=%s profile=%u/%u/%u\n", MQTT_DEVICE_ID,
    MQTT_USE_TLS ? "TLS" : "LAN_PLAINTEXT", PPG_EFFECTIVE_RATE_HZ, IMU_SAMPLE_RATE_HZ, GSR_SAMPLE_RATE_HZ);
  snapshotQueue = xQueueCreate(1, sizeof(asd::ReadingSnapshot));
  inbox = xQueueCreate(8, sizeof(Packet));
  published = xQueueCreate(16, sizeof(int));
  subscribed = xQueueCreate(4, sizeof(int));
  if (!snapshotQueue || !inbox || !published || !subscribed ||
      xTaskCreate(networkTask, "asd-network", 12288, nullptr, 1, &worker) != pdPASS) {
    Serial.println("[MQTT] Khong tao duoc task/queue; van giu sensing/Serial.");
    if (snapshotQueue) { vQueueDelete(snapshotQueue); snapshotQueue = nullptr; }
    if (inbox) { vQueueDelete(inbox); inbox = nullptr; }
    if (published) { vQueueDelete(published); published = nullptr; }
    if (subscribed) { vQueueDelete(subscribed); subscribed = nullptr; }
    return false;
  }
  return true;
}
void mqttUpdateSnapshot(const asd::ReadingSnapshot& snapshot) {
  if (snapshotQueue) xQueueOverwrite(snapshotQueue, &snapshot);
}
void mqttRecordSensing(uint32_t now, uint32_t ppgSamples, bool imuNew, bool gsrNew) {
  portENTER_CRITICAL(&statsMux);
  if (haveLoop) stats.maxLoopGapMs = std::max(stats.maxLoopGapMs, now - previousLoop);
  previousLoop = now; haveLoop = true; ++stats.sensingLoops;
  stats.ppgSamples += ppgSamples; stats.imuSamples += imuNew; stats.gsrSamples += gsrNew;
  portEXIT_CRITICAL(&statsMux);
}
MqttStats mqttGetStats() {
  portENTER_CRITICAL(&statsMux); auto copy = stats; portEXIT_CRITICAL(&statsMux); return copy;
}

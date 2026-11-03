#pragma once
// Logic giao thức độc lập Arduino để chạy đúng cùng mã trong native tests.
#include <ArduinoJson.h>
#include <array>
#include <cstdint>
#include <deque>
#include <functional>
#include <string>

namespace asd {
constexpr size_t kMaxPayload = 4096;
constexpr uint64_t kMaxInteger = 9007199254740991ULL;
struct Profile {
  uint32_t ppg = 50, imu = 50, gsr = 20;
};
struct Outbound {
  std::string suffix, payload;
  int qos = 1;
  bool retain = false;
};
struct ReadingSnapshot {
  uint64_t capturedAtMs = 0;
  float heartRate = 0, gsrDeltaPercent = 0, baselineConductance = 0;
  uint16_t gsrAdc = 0;
  uint32_t heartRateAgeMs = UINT32_MAX, ppgAgeMs = UINT32_MAX,
           gsrAgeMs = UINT32_MAX, imuAgeMs = UINT32_MAX;
  bool heartRateValid = false, gsrValid = false, gsrReadable = false;
  bool gsrCalibrating = false, imuCalibrating = false;
};
bool validId(const std::string& value);
bool parseObject(const std::string& wire, JsonDocument& document);
std::string telemetryJson(const ReadingSnapshot& snapshot, uint64_t now,
    uint64_t timestamp, const std::string& device, const std::string& origin,
    const std::string& firmware, const std::string& session);

class SessionProtocol {
 public:
  using IdFactory = std::function<std::string()>;
  SessionProtocol(std::string device, std::string origin, std::string firmware,
                  std::string boot, Profile profile, IdFactory ids);
  void connected(const std::string& connection, uint64_t now);
  void disconnected();
  void tick(uint64_t now);
  void requestSynchronization(uint64_t now) { nextSync_ = now; }
  void transportPending(size_t count, size_t bytes) { externalCount_ = count; externalBytes_ = bytes; }
  bool receive(const std::string& suffix, const std::string& payload,
               bool retained, uint64_t now);
  bool pop(Outbound& output);
  bool telemetry(const ReadingSnapshot& snapshot, uint64_t now, Outbound& output) const;
  std::string presence(bool online) const;
  const std::string& state() const { return state_; }
  const std::string& session() const { return session_; }
  uint64_t generation() const { return generation_; }
  uint64_t epoch() const { return epoch_; }
  bool authorized(uint64_t now) const;
  uint32_t rejected() const { return rejected_; }
  uint32_t dropped() const { return dropped_; }
  uint32_t starts() const { return starts_; }
  const std::string& lastError() const { return error_; }
 private:
  struct Cached {
    std::string id, session, action, fingerprint, result, reason;
    uint64_t generation = 0, timestamp = 0;
  };
  void envelope(JsonDocument& document, const char* type) const;
  void appendAck(JsonObject target, const Cached& ack) const;
  void sendAck(const Cached& ack);
  bool command(JsonObjectConst document, uint64_t now);
  bool response(JsonObjectConst document, uint64_t now);
  bool emit(const std::string& suffix, const JsonDocument& document, bool retain = false);
  bool header(JsonObjectConst document) const;
  bool fail(const char* reason);
  std::string device_, origin_, firmware_, boot_, connection_, request_;
  Profile profile_;
  IdFactory ids_;
  std::string state_ = "IDLE", session_, error_;
  uint64_t epoch_ = 0, generation_ = 0, sentAt_ = 0, confirmedAt_ = 0, nextSync_ = 0;
  bool connected_ = false, synced_ = false, confirmed_ = false, hasRequest_ = false;
  std::array<Cached, 8> cache_{};
  size_t cacheIndex_ = 0, lastIndex_ = 0;
  bool hasAck_ = false;
  uint32_t rejected_ = 0, dropped_ = 0, starts_ = 0;
  size_t outgoingBytes_ = 0;
  size_t externalCount_ = 0, externalBytes_ = 0;
  std::deque<Outbound> outgoing_;
};
}  // namespace asd

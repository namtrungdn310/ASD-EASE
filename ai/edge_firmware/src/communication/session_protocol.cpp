#include "communication/session_protocol.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <initializer_list>
#include <vector>

namespace asd {
namespace {
bool keys(JsonObjectConst object, std::initializer_list<const char*> names) {
  if (object.size() != names.size()) return false;
  for (const char* name : names) if (object[name].isUnbound()) return false;
  return true;
}
bool integer(JsonVariantConst value, uint64_t minimum = 0, uint64_t maximum = kMaxInteger) {
  return !value.is<bool>() && value.is<uint64_t>() && value.as<uint64_t>() >= minimum && value.as<uint64_t>() <= maximum;
}
std::string text(JsonVariantConst value) {
  return value.is<const char*>() ? value.as<std::string>() : std::string();
}
bool identifier(JsonVariantConst value, bool nullable = false) {
  return (nullable && value.isNull()) || (value.is<const char*>() && validId(text(value)));
}
void optionalId(JsonObject object, const char* key, const std::string& value) {
  if (value.empty()) object[key] = nullptr;
  else object[key] = value;
}
bool fresh(uint32_t age, uint64_t captured, uint64_t now, uint64_t ttl) {
  return now >= captured && now - captured <= ttl && age <= ttl - (now - captured);
}
// ArduinoJson ghi đè khoá lặp. Chặn trước, bao gồm escaped key (schema dùng ASCII).
bool uniqueKeys(const std::string& wire) {
  std::vector<std::vector<std::string>> stack;
  bool started = false;
  for (size_t i = 0; i < wire.size(); ++i) {
    char c = wire[i];
    if (stack.empty()) {
      if (c == ' ' || c == '\r' || c == '\n' || c == '\t') continue;
      if (started || c != '{') return false;
      started = true;
    }
    if (c == '{' || c == '[') {
      if (stack.size() >= 8) return false;
      stack.emplace_back();
    } else if (c == '}' || c == ']') {
      if (stack.empty()) return false;
      stack.pop_back();
    } else if (c == '"') {
      size_t start = ++i;
      bool escaped = false;
      for (; i < wire.size() && wire[i] != '"'; ++i) {
        if (wire[i] == '\\') { escaped = true; ++i; }
      }
      if (i >= wire.size()) return false;
      size_t next = wire.find_first_not_of(" \r\n\t", i + 1);
      if (next != std::string::npos && wire[next] == ':') {
        if (escaped || stack.empty()) return false;
        std::string key = wire.substr(start, i - start);
        if (std::find(stack.back().begin(), stack.back().end(), key) != stack.back().end()) return false;
        stack.back().push_back(key);
      }
    }
  }
  return stack.empty();
}
}  // namespace

bool validId(const std::string& value) {
  if (value.empty() || value.size() > 64) return false;
  for (size_t i = 0; i < value.size(); ++i) {
    char c = value[i];
    bool alnum = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9');
    if (!alnum && (i == 0 || (c != '_' && c != '-'))) return false;
  }
  return true;
}
bool parseObject(const std::string& wire, JsonDocument& document) {
  if (wire.empty() || wire.size() > kMaxPayload || wire.find('\0') != std::string::npos || !uniqueKeys(wire)) return false;
  return !deserializeJson(document, wire, DeserializationOption::NestingLimit(8)) && document.is<JsonObject>();
}

std::string telemetryJson(const ReadingSnapshot& s, uint64_t now, uint64_t timestamp,
    const std::string& device, const std::string& origin, const std::string& firmware, const std::string& session) {
  if (!validId(device) || (!session.empty() && !validId(session)) || timestamp > kMaxInteger ||
      (origin != "DEVICE" && origin != "SYNTHETIC") || firmware.empty() || firmware.size() > 64) return {};
  JsonDocument d;
  d["schema_version"] = "1.0";
  d["device_id"] = device;
  optionalId(d.as<JsonObject>(), "session_id", session);
  d["timestamp_ms"] = timestamp;
  d["data_origin"] = origin;
  bool ppgFresh = fresh(s.ppgAgeMs, s.capturedAtMs, now, 1000);
  if (s.heartRateValid && ppgFresh && fresh(s.heartRateAgeMs, s.capturedAtMs, now, 3000) &&
      std::isfinite(s.heartRate) && s.heartRate >= 20 && s.heartRate <= 240) d["hr_bpm"] = std::round(s.heartRate * 10) / 10;
  else d["hr_bpm"] = nullptr;
  bool gsrFresh = fresh(s.gsrAgeMs, s.capturedAtMs, now, 1000);
  if (s.gsrReadable && gsrFresh && s.gsrAdc <= 4095) d["gsr"]["raw"] = s.gsrAdc;
  else d["gsr"]["raw"] = nullptr;
  if (s.gsrValid && gsrFresh && s.baselineConductance > 0.05f && std::isfinite(s.baselineConductance) && std::isfinite(s.gsrDeltaPercent))
    d["gsr"]["delta"] = s.gsrDeltaPercent / 100.0f;
  else d["gsr"]["delta"] = nullptr;
  d["movement"]["score"] = nullptr;
  d["signal_quality"]["ppg"] = 0;
  d["signal_quality"]["gsr"] = 0;
  d["signal_quality"]["imu"] = 0;
  d["prediction"]["probability"] = nullptr;
  bool calibrating = (s.gsrCalibrating && gsrFresh) || (s.imuCalibrating && fresh(s.imuAgeMs, s.capturedAtMs, now, 1000));
  d["prediction"]["state"] = calibrating ? "CALIBRATING" : "UNCERTAIN";
  d["firmware_version"] = firmware;
  d["model_version"] = "none";
  std::string output;
  serializeJson(d, output);
  return output.size() <= kMaxPayload ? output : std::string();
}

SessionProtocol::SessionProtocol(std::string device, std::string origin, std::string firmware,
    std::string boot, Profile profile, IdFactory ids)
  : device_(device), origin_(origin), firmware_(firmware), boot_(boot), profile_(profile), ids_(ids) {}

void SessionProtocol::envelope(JsonDocument& d, const char* type) const {
  d["control_version"] = "1.0"; d["message_type"] = type;
  d["device_id"] = device_; d["data_origin"] = origin_;
  d["boot_id"] = boot_; d["connection_id"] = connection_;
}
bool SessionProtocol::emit(const std::string& suffix, const JsonDocument& d, bool retain) {
  std::string payload; serializeJson(d, payload);
  if (payload.size() > kMaxPayload || outgoing_.size() + externalCount_ >= 8 || outgoingBytes_ + externalBytes_ + payload.size() > 32768) {
    ++dropped_; return false;
  }
  outgoing_.push_back({suffix, payload, 1, retain}); outgoingBytes_ += payload.size(); return true;
}
bool SessionProtocol::pop(Outbound& output) {
  if (outgoing_.empty()) return false;
  output = std::move(outgoing_.front()); outgoing_.pop_front(); outgoingBytes_ -= output.payload.size(); return true;
}
void SessionProtocol::connected(const std::string& connection, uint64_t now) {
  disconnected(); connection_ = connection; connected_ = validId(connection) && validId(device_) && validId(boot_);
  nextSync_ = now;
}
void SessionProtocol::disconnected() {
  connected_ = synced_ = confirmed_ = hasRequest_ = false;
  outgoing_.clear(); outgoingBytes_ = 0;
  externalCount_ = externalBytes_ = 0;
}
bool SessionProtocol::authorized(uint64_t now) const {
  return connected_ && synced_ && confirmed_ && now >= confirmedAt_ && now - confirmedAt_ < 30000;
}
bool SessionProtocol::header(JsonObjectConst d) const {
  return text(d["control_version"]) == "1.0" && text(d["device_id"]) == device_ &&
         text(d["data_origin"]) == origin_ && text(d["boot_id"]) == boot_ && text(d["connection_id"]) == connection_;
}
bool SessionProtocol::fail(const char* reason) { ++rejected_; error_ = reason; return false; }
std::string SessionProtocol::presence(bool online) const {
  JsonDocument d; envelope(d, "PRESENCE"); d["status"] = online ? "ONLINE" : "OFFLINE";
  std::string output; serializeJson(d, output); return output;
}
void SessionProtocol::appendAck(JsonObject d, const Cached& ack) const {
  d["control_version"] = "1.0"; d["message_type"] = "ACK";
  d["device_id"] = device_; d["data_origin"] = origin_; d["boot_id"] = boot_; d["connection_id"] = connection_;
  d["request_id"] = request_; d["command_id"] = ack.id; d["generation"] = ack.generation;
  d["session_id"] = ack.session; d["action"] = ack.action; d["result"] = ack.result; d["timestamp_ms"] = ack.timestamp;
  if (ack.reason.empty()) d["reason"] = nullptr; else d["reason"] = ack.reason;
  if (ack.result != "STOPPED") d["final_summary"] = nullptr;
  else {
    JsonObject summary = d["final_summary"].to<JsonObject>();
    summary["cutoff_timestamp_ms"] = 0; summary["final_batch_id"] = nullptr;
    summary["total_generated_batches"] = 0; summary["dropped_batches"] = 0;
    for (const char* stream : {"ppg", "imu", "gsr"}) {
      summary["slot_counts"][stream] = 0; summary["missing_samples"][stream] = 0;
    }
    summary["dropped_batch_ranges"].to<JsonArray>();
    summary["loss_ranges_truncated"] = false; summary["raw_recording_enabled"] = false;
  }
}
void SessionProtocol::sendAck(const Cached& ack) {
  JsonDocument d; appendAck(d.to<JsonObject>(), ack); emit("ack", d);
}
void SessionProtocol::tick(uint64_t now) {
  if (!connected_ || now < nextSync_) return;
  std::string next = ids_();
  if (!validId(next)) { fail("INVALID_REQUEST_ID"); return; }
  request_ = next; sentAt_ = now; hasRequest_ = true;
  JsonDocument d; envelope(d, "STATE_REQUEST"); d["request_id"] = request_;
  d["actual_state"] = state_; optionalId(d.as<JsonObject>(), "session_id", session_);
  if (hasAck_) d["last_command_id"] = cache_[lastIndex_].id; else d["last_command_id"] = nullptr;
  d["last_generation"] = generation_; d["timestamp_ms"] = state_ == "RECORDING" ? now - epoch_ : now;
  if (hasAck_) appendAck(d["last_ack"].to<JsonObject>(), cache_[lastIndex_]); else d["last_ack"] = nullptr;
  emit("state/request", d);
  nextSync_ = now + (hasAck_ && !confirmed_ ? 1000 : 15000);
}

bool SessionProtocol::command(JsonObjectConst d, uint64_t now) {
  if (!keys(d, {"control_version","message_type","device_id","data_origin","boot_id","connection_id",
      "request_id","command_id","generation","session_id","action","expires_in_ms","acquisition_profile"}) ||
      !header(d) || text(d["message_type"]) != "COMMAND" || !identifier(d["command_id"]) || !identifier(d["session_id"]) ||
      !integer(d["generation"], 1) || !integer(d["expires_in_ms"], 1, 30000)) return fail("SCHEMA_INVALID");
  if (!synced_ || !hasRequest_ || text(d["request_id"]) != request_ || now < sentAt_ || now - sentAt_ >= d["expires_in_ms"].as<uint64_t>()) return fail("LEASE_EXPIRED");
  std::string action = text(d["action"]);
  if (action != "START" && action != "STOP") return fail("SCHEMA_INVALID");
  auto profile = d["acquisition_profile"].as<JsonObjectConst>();
  if (action == "START" && (!keys(profile, {"ppg_hz","imu_hz","gsr_hz","window_ms"}) ||
      !integer(profile["ppg_hz"],1,1000) || !integer(profile["imu_hz"],1,1000) ||
      !integer(profile["gsr_hz"],1,1000) || !integer(profile["window_ms"],1000,1000))) return fail("SCHEMA_INVALID");
  if (action == "STOP" && !d["acquisition_profile"].isNull()) return fail("SCHEMA_INVALID");
  std::string fingerprint = action + ":" + text(d["session_id"]) + ":" + std::to_string(d["generation"].as<uint64_t>());
  if (action == "START") fingerprint += ":" + std::to_string(profile["ppg_hz"].as<unsigned>()) + ":" + std::to_string(profile["imu_hz"].as<unsigned>()) + ":" + std::to_string(profile["gsr_hz"].as<unsigned>());
  for (const auto& cached : cache_) if (cached.id == text(d["command_id"])) {
    if (cached.fingerprint != fingerprint) return fail("COMMAND_CONFLICT");
    if (cached.generation < generation_) return fail("STALE_COMMAND");
    sendAck(cached); return true;
  }
  Cached ack;
  ack.id = text(d["command_id"]); ack.session = text(d["session_id"]); ack.action = action;
  ack.generation = d["generation"].as<uint64_t>(); ack.fingerprint = fingerprint;
  if (ack.generation <= generation_) return fail("STALE_COMMAND");
  ack.result = "REJECTED";
  if (action == "START") {
    if (profile["ppg_hz"].as<uint32_t>() != profile_.ppg || profile["imu_hz"].as<uint32_t>() != profile_.imu || profile["gsr_hz"].as<uint32_t>() != profile_.gsr) ack.reason = "PROFILE_UNSUPPORTED";
    else if (state_ == "RECORDING") ack.reason = "BUSY";
    else { state_ = "RECORDING"; session_ = ack.session; epoch_ = now; ++starts_; ack.result = "STARTED"; }
  } else if (!session_.empty() && ack.session != session_ && state_ == "RECORDING") ack.reason = "SESSION_NOT_ACCEPTING";
  else { state_ = "STOPPED"; session_ = ack.session; ack.result = "STOPPED"; }
  generation_ = ack.generation;
  cache_[cacheIndex_] = ack; lastIndex_ = cacheIndex_; cacheIndex_ = (cacheIndex_ + 1) % cache_.size();
  hasAck_ = true; confirmed_ = false; sendAck(ack); nextSync_ = now;
  return true;
}

bool SessionProtocol::response(JsonObjectConst d, uint64_t now) {
  if (!keys(d, {"control_version","message_type","device_id","data_origin","boot_id","connection_id",
      "request_id","session_id","state","generation","accepted_command_id","pending_command","error_code"}) ||
      !header(d) || text(d["message_type"]) != "STATE_RESPONSE" || !identifier(d["session_id"], true) ||
      !identifier(d["accepted_command_id"], true) || !identifier(d["error_code"], true) || !integer(d["generation"])) return fail("SCHEMA_INVALID");
  if (!hasRequest_ || text(d["request_id"]) != request_ || now < sentAt_ || now - sentAt_ >= 30000) return fail("LEASE_EXPIRED");
  if (d["generation"].as<uint64_t>() < generation_) return fail("STALE_COMMAND");
  std::string state = text(d["state"]);
  if (state != "IDLE" && state != "STARTING" && state != "RECORDING" && state != "STOPPING" && state != "STOPPED" && state != "ABORTED") return fail("SCHEMA_INVALID");
  if (!d["pending_command"].isNull() && !d["pending_command"].is<JsonObjectConst>()) return fail("SCHEMA_INVALID");
  synced_ = true; confirmedAt_ = now;
  if (!d["error_code"].isNull()) { confirmed_ = false; error_ = text(d["error_code"]); }
  else if (!hasAck_ && state_ != "RECORDING") confirmed_ = true;
  else if (hasAck_) {
    const auto& ack = cache_[lastIndex_];
    confirmed_ = d["error_code"].isNull() && text(d["accepted_command_id"]) == ack.id && text(d["session_id"]) == session_ &&
      ((ack.result == "STARTED" && (state == "RECORDING" || state == "STOPPING")) ||
       (ack.result == "STOPPED" && (state == "STOPPED" || state == "STOPPING")) || ack.result == "REJECTED");
  }
  if (state == "ABORTED" && state_ == "RECORDING") { state_ = "STOPPED"; confirmed_ = false; nextSync_ = now; }
  else if (state == "ABORTED" && state_ == "STOPPED" && d["error_code"].isNull()) confirmed_ = true;
  if (!d["pending_command"].isNull()) {
    if (!d["error_code"].isNull() && text(d["pending_command"]["action"]) != "STOP") return fail("SESSION_NOT_ACCEPTING");
    return command(d["pending_command"].as<JsonObjectConst>(), now);
  }
  generation_ = std::max(generation_, d["generation"].as<uint64_t>());
  return true;
}
bool SessionProtocol::receive(const std::string& suffix, const std::string& payload, bool retained, uint64_t now) {
  if (!connected_ || retained) return fail("RETAINED_OR_DISCONNECTED");
  JsonDocument d;
  if (!parseObject(payload, d)) return fail("MALFORMED_JSON");
  if (suffix == "command") return command(d.as<JsonObjectConst>(), now);
  if (suffix == "state/response") return response(d.as<JsonObjectConst>(), now);
  return fail("TOPIC_NOT_ALLOWED");
}
bool SessionProtocol::telemetry(const ReadingSnapshot& s, uint64_t now, Outbound& output) const {
  if (!authorized(now)) return false;
  auto payload = telemetryJson(s, now, state_ == "RECORDING" ? now - epoch_ : now,
      device_, origin_, firmware_, state_ == "RECORDING" ? session_ : std::string());
  if (payload.empty()) return false;
  output = {"telemetry", payload, 0, false}; return true;
}
}  // namespace asd

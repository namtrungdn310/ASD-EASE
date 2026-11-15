#include "communication/session_protocol.h"
#include "processing/movement_score.h"
#include <iostream>
#include <limits>
#include <memory>

// Chỉ harness native: clock/đầu vào giả và stdout NDJSON; core cùng mã với ESP32.
int main() {
  std::unique_ptr<asd::SessionProtocol> protocol;
  asd::MovementScoreEstimator movement;
  unsigned nonce = 0;
  std::string line;
  while (std::getline(std::cin, line)) {
    JsonDocument input, result;
    if (deserializeJson(input, line)) return 2;
    std::string operation = input["op"] | "";
    uint64_t now = input["now"] | uint64_t(0);
    bool accepted = true;
    if (operation == "init") {
      movement.reset();
      asd::Profile profile;
      profile.ppg = input["profile"]["ppg_hz"] | 50;
      profile.imu = input["profile"]["imu_hz"] | 50;
      profile.gsr = input["profile"]["gsr_hz"] | 20;
      protocol.reset(new asd::SessionProtocol(input["device_id"] | "SYN-FIRMWARE", input["data_origin"] | "SYNTHETIC",
        "native-firmware-test", input["boot_id"] | "BOOT-NATIVE", profile, [&nonce] { return "REQ-" + std::to_string(++nonce); }));
    } else if (!protocol) return 3;
    else if (operation == "connect") protocol->connected(input["connection_id"] | "CONN-NATIVE", now);
    else if (operation == "disconnect") protocol->disconnected();
    else if (operation == "tick") protocol->tick(now);
    else if (operation == "resync") protocol->requestSynchronization(now);
    else if (operation == "motion_reset") movement.reset();
    else if (operation == "budget") protocol->transportPending(input["count"] | 0U, input["bytes"] | 0U);
    else if (operation == "burst") {
      std::string wire; serializeJson(input["payload"], wire);
      for (unsigned i=0; i<20; ++i) protocol->receive("command", wire, false, now);
    }
    else if (operation == "receive") {
      std::string wire;
      if (input["wire"].is<const char*>()) wire = input["wire"].as<std::string>();
      else serializeJson(input["payload"], wire);
      accepted = protocol->receive(input["suffix"] | "command", wire, input["retain"] | false, now);
    } else if (operation == "motion") {
      auto sample = input["sample"];
      asd::MovementScoreEstimator::Reading reading;
      if (input["sensor_valid"] | true) {
        const float missing = std::numeric_limits<float>::quiet_NaN();
        reading = movement.update(now, sample["ax"] | missing, sample["ay"] | missing,
            sample["az"] | missing, sample["gx"] | missing,
            sample["gy"] | missing, sample["gz"] | missing);
      } else movement.reset();
      result["motion"]["valid"] = reading.valid;
      if (reading.valid) result["motion"]["score"] = reading.score;
      else result["motion"]["score"] = nullptr;
      asd::ReadingSnapshot snapshot;
      snapshot.capturedAtMs = now;
      snapshot.imuAgeMs = 0;
      snapshot.movementScore = reading.score;
      snapshot.movementValid = reading.valid;
      JsonDocument frame;
      deserializeJson(frame, asd::telemetryJson(snapshot, now, now,
          "SYN-FIRMWARE", "SYNTHETIC", "native-motion-test", ""));
      result["telemetry"] = frame;
    } else if (operation == "telemetry") {
      asd::ReadingSnapshot s;
      auto v = input["snapshot"];
      s.capturedAtMs = v["captured_at_ms"] | now;
      s.heartRate = v["hr"] | 0.0f;
      s.heartRateValid = v["hr_valid"] | false;
      s.heartRateAgeMs = v["hr_age"] | UINT32_MAX;
      s.ppgAgeMs = v["ppg_age"] | UINT32_MAX;
      s.gsrAdc = v["gsr_adc"] | uint16_t(0);
      s.gsrAgeMs = v["gsr_age"] | UINT32_MAX;
      s.imuAgeMs = v["imu_age"] | UINT32_MAX;
      s.movementScore = v["movement_score"] | 0.0f;
      s.movementValid = v["movement_valid"] | false;
      s.imuValid = v["imu_valid"] | false;
      const char* axes[] = {"x", "y", "z"};
      for (size_t i = 0; i < 3; ++i) {
        s.acceleration[i] = v["acceleration"][axes[i]] | std::numeric_limits<float>::quiet_NaN();
        s.angularVelocity[i] = v["angular_velocity"][axes[i]] | std::numeric_limits<float>::quiet_NaN();
      }
      s.gsrDeltaPercent = v["gsr_percent"] | 0.0f;
      s.baselineConductance = v["gsr_baseline"] | 0.0f;
      s.gsrReadable = v["gsr_readable"] | false;
      s.gsrValid = v["gsr_valid"] | false;
      s.gsrCalibrating = v["gsr_calibrating"] | false;
      s.imuCalibrating = v["imu_calibrating"] | false;
      asd::Outbound output;
      accepted = protocol->telemetry(s, now, output);
      if (accepted) {
        JsonDocument payload; deserializeJson(payload, output.payload);
        result["telemetry"] = payload;
      }
    } else return 4;
    result["accepted"] = accepted;
    if (protocol) {
      result["state"] = protocol->state(); result["session_id"] = protocol->session();
      result["generation"] = protocol->generation(); result["epoch"] = protocol->epoch();
      result["authorized"] = protocol->authorized(now); result["starts"] = protocol->starts();
      result["rejected"] = protocol->rejected(); result["dropped"] = protocol->dropped(); result["error"] = protocol->lastError();
      asd::Outbound packet;
      JsonArray packets = result["out"].to<JsonArray>();
      while (protocol->pop(packet)) {
        JsonObject item = packets.add<JsonObject>();
        item["suffix"] = packet.suffix; item["qos"] = packet.qos; item["retain"] = packet.retain;
        JsonDocument payload; deserializeJson(payload, packet.payload); item["payload"] = payload;
      }
      if (operation != "init") {
        JsonDocument presence; deserializeJson(presence, protocol->presence(false)); result["will"] = presence;
      }
    }
    serializeJson(result, std::cout); std::cout << std::endl;
  }
}

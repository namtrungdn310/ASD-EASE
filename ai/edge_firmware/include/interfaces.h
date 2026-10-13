#pragma once
#include <Arduino.h>

enum class Availability { NOT_IMPLEMENTED, UNAVAILABLE, READY, ERROR };
enum class EngineeringState { NORMAL, ATTENTION, UNCERTAIN, CALIBRATING };

struct TelemetryFrame {
  const char* schemaVersion;
  const char* deviceId;
  unsigned long timestampMs;
  bool synthetic;
  bool hrAvailable;
  float hrBpm;
  float ppgQuality;
  float gsrQuality;
  float imuQuality;
  EngineeringState state;
};

class SignalProcessor { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };
class SignalQualityManager { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };
class BaselineManager { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };
class FeatureExtractor { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };
class EdgeModel { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };
class StateMachine { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };
class TelemetryClient { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };
class RawBatchClient { public: Availability begin() { return Availability::NOT_IMPLEMENTED; } };


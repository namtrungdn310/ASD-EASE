# System Architecture

## Boundaries

The project is an engineering research prototype, not a medical device, clinical diagnostic or treatment system. Deployment-facing states are `NORMAL`, `ATTENTION`, `UNCERTAIN`, plus operational `CALIBRATING`, `DISCONNECTED`, and `ERROR`. `ATTENTION` is an engineering criterion, not an anxiety diagnosis.

## Three modes

1. Development: host USB may flash and debug the ESP32.
2. R&D/data collection: the ESP32 sends synchronized raw batches through Wi-Fi for offline software/model development.
3. Competition/Edge: battery-powered ESP32 performs the final signal pipeline and state decision; laptop receives compact telemetry and serves the dashboard on the same offline-capable LAN.

## Locked competition flow

```text
MAX30102 + MPU6050 + GSR
  -> acquisition and preprocessing
  -> signal quality (bad quality may yield UNCERTAIN)
  -> personal baseline
  -> shared feature definitions
  -> Edge model
  -> temporal state logic
  -> bounded telemetry queue
  -> local Wi-Fi/LAN
  -> FastAPI receiver -> SQLite metadata/raw files -> WebSocket -> React dashboard
```

The laptop never performs final competition feature extraction, inference, temporal decision or alert decision. No Internet or USB data link is required in competition mode.

## Network resilience design

Acquisition, processing, inference and state updates run independently of network sending. Telemetry enters a bounded queue. If Wi-Fi is unavailable, the firmware drops or limits telemetry and retries later without blocking acquisition or inference. Detailed implementation is gated to Phase 21.

## Storage

SQLite stores device/session/annotation/event and useful low-rate metadata. High-rate raw sensor batches use research files (JSONL in V1), never one SQLite row per sample.

## Synthetic development path

The synthetic generator models shared scenario variables, creates raw streams under the same API schema, passes them through the same preprocessing entry point and can be replayed by the mock device. It is R&D infrastructure only and does not change competition architecture or verify physical sensors.

## Future AI path

```text
raw -> preprocessing -> quality -> baseline -> rolling windows -> features
    -> simple rules / small models -> probability -> temporal state machine
```

Python and C++ will eventually share definitions and golden test vectors. No production model or parity claim exists in the scaffold.


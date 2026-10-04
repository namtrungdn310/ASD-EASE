# API Contract

This file is the authoritative contract for firmware, simulator, backend, generated datasets and frontend. Schema `1.0` uses JSON, UTF-8 and field names exactly as shown. Unknown fields are rejected by backend ingestion models.

## Timestamp semantics

`timestamp_ms` and `start_timestamp_ms` are non-negative milliseconds since the start of the current acquisition session, not wall-clock time. Raw arrays are ordered. With no per-sample timestamps in a raw batch, sample `i` occurs at `start_timestamp_ms + i * 1000 / sample_rate_hz`. Generated session files additionally keep per-stream timestamps when configured jitter must be preserved. Missing samples remain in position as JSON `null`; samples are never silently removed or shuffled.

## Compact telemetry — `POST /api/v1/telemetry`

Nominal development cadence is 1 Hz and configurable. A successful validation returns HTTP 202.

| Field | Type | Unit/range | Nullable | Meaning/missing behavior |
|---|---|---|---|---|
| `schema_version` | string | exactly `1.0` | no | Contract version. |
| `device_id` | string | pseudonymous, max 64 | no | Device/simulator identifier. |
| `session_id` | string | max 64 | yes | `null` when no active session. |
| `timestamp_ms` | integer | ms, >=0 | no | Session-relative sample time. |
| `data_origin` | enum | `DEVICE`, `SYNTHETIC` | no | Cannot silently treat simulator data as device data. |
| `hr_bpm` | number | bpm, 20–240 | yes | Estimated HR; `null` when unavailable/invalid. |
| `gsr.raw` | integer | ADC count, 0–4095 | yes | Assumed 12-bit count; not calibrated conductance. |
| `gsr.delta` | number | baseline-relative ratio | yes | `null` before baseline/when invalid. |
| `movement.score` | number | unitless, 0–1 | yes | Engineering summary, definition not scientifically final. |
| `signal_quality.ppg` | number | 0–1 | no | PPG engineering quality. |
| `signal_quality.gsr` | number | 0–1 | no | GSR/contact engineering quality. |
| `signal_quality.imu` | number | 0–1 | no | IMU engineering quality. |
| `prediction.probability` | number | 0–1 | yes | Engineering-model score; `null` for unavailable/quality-gated states. |
| `prediction.state` | enum | `NORMAL`, `ATTENTION`, `UNCERTAIN`, `CALIBRATING` | no | Engineering state only. |
| `firmware_version` | string | semantic/free version | no | `simulator-*` for mock device. |
| `model_version` | string | version or `none` | no | `none` means no Edge model. |

Example:

```json
{"schema_version":"1.0","device_id":"SIM-001","session_id":"SYN-SESSION001","timestamp_ms":0,"data_origin":"SYNTHETIC","hr_bpm":78.4,"gsr":{"raw":1842,"delta":0.13},"movement":{"score":0.42},"signal_quality":{"ppg":0.91,"gsr":0.87,"imu":1.0},"prediction":{"probability":0.74,"state":"ATTENTION"},"firmware_version":"simulator-0.1.0","model_version":"none"}
```

## Raw batch — `POST /api/v1/raw-batch`

Development defaults are PPG 100 Hz, IMU 50 Hz and GSR 20 Hz; these are configurable engineering examples, not validated sampling parameters. A successful file append returns HTTP 202.

| Field | Type | Unit/range | Nullable | Meaning |
|---|---|---|---|---|
| common version/device/session | strings | as above | no | Raw batches require an active session ID. |
| `batch_id` | integer | >=0 | no | Monotonic within a session. |
| `start_timestamp_ms` | integer | ms, >=0 | no | Time of index 0 in every stream. |
| `data_origin` | enum | `DEVICE`, `SYNTHETIC` | no | Provenance marker. |
| `ppg.sample_rate_hz` | number | Hz, >0 | no | Reconstruction frequency. |
| `ppg.red`, `ppg.ir` | arrays | MAX30102 sample counts, expected 0–262143 | elements may be null | Arrays must have equal length. |
| `imu.sample_rate_hz` | number | Hz, >0 | no | Reconstruction frequency. |
| `imu.ax/ay/az` | arrays | g | elements may be null | Equal-length axes. |
| `imu.gx/gy/gz` | arrays | degrees/s | elements may be null | Equal-length axes. |
| `gsr.sample_rate_hz` | number | Hz, >0 | no | Reconstruction frequency. |
| `gsr.adc` | array | ADC counts, expected 0–4095 | elements may be null | Raw counts lack validated conductance conversion. |

## Other endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Receiver readiness. |
| GET | `/api/v1/devices` | Last-seen device metadata. |
| POST | `/api/v1/sessions/start` | Start pseudonymous session. |
| POST | `/api/v1/sessions/stop` | Stop session. |
| GET | `/api/v1/sessions` | List sessions. |
| POST | `/api/v1/annotations` | Store research annotation. |
| GET | `/api/v1/events` | List latest engineering events. |
| WS | `/api/v1/ws/live` | Broadcast every accepted compact telemetry payload. |

Contract changes must update this document, Pydantic, TypeScript and C++ representations together.


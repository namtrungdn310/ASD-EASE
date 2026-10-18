# Project Progress

## Current Phase

Phase 02 — Mock End-to-End

## Overall Status

IN_PROGRESS

## Progress Table

| Phase | Name | Owner | Status | Started | Completed | Notes |
|---|---|---|---|---|---|---|
| 00 | Hardware Verification | AUTOMATION | NOT_STARTED | - | - | Physical verification required. |
| 01 | Project Scaffold | IT | DONE | - | - | Structure, tests, builds and containers verified; PlatformIO compilation passed. This does not verify physical hardware. |
| 02 | Mock End-to-End | IT | IN_PROGRESS | - | - | Generator, HTTP/raw ingest, live WebSocket and reconnect verified; visual browser inspection remains. |
| 03 | MAX30102 | AUTOMATION | IN_PROGRESS | - | - | Driver/FIFO/HR implementation in PR #7; physical acceptance evidence pending. |
| 04 | MPU6050 | AUTOMATION | IN_PROGRESS | - | - | Register-read/EMA implementation in PR #7; physical calibration/timing evidence pending. |
| 05 | GSR | AUTOMATION | IN_PROGRESS | - | - | ADC/baseline/EMA implementation in PR #7; GPIO and conductance conversion evidence pending. |
| 06 | Sensor Integration | AUTOMATION | IN_PROGRESS | - | - | Combined dual-I2C/ADC Serial loop in PR #7; actual alignment/rates/loss evidence pending. |
| 07 | Wi-Fi Backend | IT | NOT_STARTED | - | - | Real ESP32 network not implemented; Automation supports hardware/driver verification. |
| 08 | Data Logger | IT | NOT_STARTED | - | - | Raw receiver scaffold does not complete phase. |
| 09 | Dataset Collection | SHARED | NOT_STARTED | - | - | Synthetic sessions do not count as real collection. |
| 10 | Signal Processing | IT | NOT_STARTED | - | - | Only shared input interface exists. |
| 11 | Baseline Features | IT | NOT_STARTED | - | - | Placeholder only. |
| 12 | Rule Baselines | IT | NOT_STARTED | - | - | No model implemented. |
| 13 | ML Experiments | IT | NOT_STARTED | - | - | No model trained. |
| 14 | Model Selection | SHARED | NOT_STARTED | - | - | No measured comparison. |
| 15 | Model Export | IT | NOT_STARTED | - | - | No model artifact. |
| 16 | Edge Inference | SHARED | NOT_STARTED | - | - | No inference implementation. |
| 17 | Parity Test | SHARED | NOT_STARTED | - | - | No parity evidence. |
| 18 | Temporal Logic | SHARED | NOT_STARTED | - | - | No production state machine. |
| 19 | Battery Standalone | AUTOMATION | NOT_STARTED | - | - | Requires hardware. |
| 20 | Competition Wireless | SHARED | NOT_STARTED | - | - | Requires hardware. |
| 21 | Network Resilience | SHARED | NOT_STARTED | - | - | Documented design only. |
| 22 | Demo Scenarios | SHARED | NOT_STARTED | - | - | Synthetic scenarios do not complete physical demo. |
| 23 | Benchmark | SHARED | NOT_STARTED | - | - | No scientific/system metrics claimed. |
| 24 | Competition Freeze | SHARED | NOT_STARTED | - | - | Future phase. |

## Current Blockers

- No controllable browser is available in the current environment, so visual confirmation of live dashboard values and the `SYNTHETIC DATA` marker is not verified.

## Current Risks

- Exact ESP32-S3 Super Mini memory configuration and GPIO mapping are not verified.
- Sensor quality, power behavior and battery architecture have not been measured.
- Browser-level visual behavior still requires verification even though the production build, HTTP serving and WebSocket path pass.
- Synthetic behavior is an engineering approximation and cannot establish physiological or clinical validity.

## Current Integration State

- Hardware: Not physically verified.
- Backend: 13 tests passed; container healthy; HTTP/OpenAPI/WebSocket and raw storage verified.
- Frontend: TypeScript/Vite build passed; container serves HTTP 200; live visual inspection not verified.
- AI: Synthetic generator and shared preprocessing input implemented; future science pipeline is scaffold only.
- Firmware: Three sensor drivers, EMA and combined Serial reporting are implemented in PR #7. The `esp32s3_supermini` environment builds; hardware acceptance remains unverified. Shared types and legacy config-header consolidation are pending manual source work in cleanup branch 01.
- Docker: Compose config, all three images and backend/frontend startup verified.
- Network: Mock HTTP/WebSocket and disconnect/reconnect replay verified; real ESP32 LAN path not implemented.
- Competition mode: Not implemented or verified.

## Latest Verified Milestone

Phase 01 — Project Scaffold completed and verified within its non-hardware scope.

## Next Action

Follow the [IT device-integration plan](integration/README.md) and update its [branch tracker](integration/PROGRESS.md). Start with repository cleanup, then verify live synthetic telemetry visually to complete the remaining Phase 02 criterion. IT now owns firmware serialization, session control, Wi-Fi/HTTP and raw batching as well as backend/frontend integration; Automation retains driver and hardware verification work.

The new plan describes future implementation and does not itself complete any phase. Real-device acceptance for Phase 07/08 remains dependent on the corresponding hardware evidence. Existing phase statuses and historical results above must be reconciled with measured evidence during the cleanup and verification branches.

## Metrics Available

No scientific metrics available yet. No accuracy, F1, latency, RAM, false-alert rate or battery-life claim has been made.

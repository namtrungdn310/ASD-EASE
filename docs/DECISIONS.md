# Architecture Decisions

Each accepted entry has no invented date (`Date: -`).

## ADR-001 — Three source modules
Status: ACCEPTED

Context: The student team needs clear ownership.

Decision: Source modules are exactly `backend`, `frontend`, and `AI`; `docs` is documentation.

Reason: Minimize maintenance overhead.

Consequences: No phase-specific duplicate source trees.

Date: -

## ADR-002 — Firmware location
Status: ACCEPTED

Context: Firmware is part of Edge AI delivery.

Decision: Firmware lives at `AI/edge_firmware`.

Reason: Avoid a fourth source module.

Consequences: Host PlatformIO operations use this directory.

Date: -

## ADR-003 — Main MCU
Status: ACCEPTED

Context: The selected MCU family is ESP32-S3.

Decision: ESP32-S3 Super Mini is the main MCU.

Reason: Project hardware selection.

Consequences: Exact variant still requires physical verification.

Date: -

## ADR-004 — Final inference on wearable
Status: ACCEPTED

Context: Competition architecture is Edge-first.

Decision: Final feature extraction, AI, temporal and alert decisions run on ESP32-S3.

Reason: Standalone, low-dependency behavior.

Consequences: Laptop inference is development-only.

Date: -

## ADR-005 — Laptop role
Status: ACCEPTED

Context: Judges need local visualization.

Decision: Laptop is receiver, optional logger and dashboard during competition.

Reason: Separate display from decision-making.

Consequences: Dashboard cannot redefine state.

Date: -

## ADR-006 — Local Wi-Fi/LAN
Status: ACCEPTED

Context: Competition telemetry must be wireless.

Decision: Wearable and laptop share a local LAN.

Reason: Removes USB data dependency.

Consequences: Backend binds `0.0.0.0`; wearable uses laptop LAN IP.

Date: -

## ADR-007 — No Internet dependency
Status: ACCEPTED

Context: Venue Internet is unreliable/unnecessary.

Decision: Competition system runs without Internet.

Reason: Repeatability.

Consequences: No cloud services in the critical path.

Date: -

## ADR-008 — Battery and no competition USB
Status: ACCEPTED

Context: The device is wearable.

Decision: ESP32 is battery-powered and USB-disconnected in competition.

Reason: Validate true standalone operation.

Consequences: Power design requires later physical verification.

Date: -

## ADR-009 — FastAPI and React
Status: ACCEPTED

Context: Two students need an understandable local stack.

Decision: FastAPI receiver plus React dashboard.

Reason: Typed contracts and simple development.

Consequences: HTTP/WebSocket form the local interface.

Date: -

## ADR-010 — Split metadata and raw storage
Status: ACCEPTED

Context: High-rate samples are unsuitable as one SQLite row each.

Decision: SQLite stores metadata; files store raw batches.

Reason: Simple research storage with manageable write load.

Consequences: Backups must cover both.

Date: -

## ADR-011 — Quality can yield UNCERTAIN
Status: ACCEPTED

Context: Forced predictions from bad signals are misleading.

Decision: Quality gates may emit `UNCERTAIN`.

Reason: Quality before classification.

Consequences: Nullable sensor/probability fields are supported.

Date: -

## ADR-012 — Compare simple baselines
Status: ACCEPTED

Context: Model complexity must be justified.

Decision: Compare ML against HR, HR+GSR and HR+GSR+IMU rules.

Reason: Interpretability and honest evaluation.

Consequences: No model is assumed to win.

Date: -

## ADR-013 — Hardware facts require verification
Status: ACCEPTED

Context: Super Mini variants differ.

Decision: No final GPIO/flash/PSRAM configuration before physical verification.

Reason: Prevent damaging or invalid assumptions.

Consequences: Conservative build profile and unset pins.

Date: -

## ADR-014 — Network cannot block Edge pipeline
Status: ACCEPTED

Context: Wi-Fi can fail.

Decision: Acquisition/inference continue with bounded telemetry behavior.

Reason: Reliability.

Consequences: Detailed queue/retry work is Phase 21.

Date: -

## ADR-015 — Synthetic provenance and shared pipeline
Status: ACCEPTED

Context: Software needs test data before real collection.

Decision: Synthetic signals use the same raw contract/preprocessing interface, separate storage and mandatory `SYNTHETIC` provenance.

Reason: Avoid incompatible test pipelines and misleading provenance.

Consequences: Synthetic-only results cannot validate real performance or auto-deploy a model.

Date: -


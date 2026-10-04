# Phase 02 — Mock End-to-End

## Status

IN_PROGRESS

## Owner

IT

## Objective

Verify synthetic generator/replay through HTTP, FastAPI validation, WebSocket and React dashboard.

## Why This Phase Exists

De-risks integration before any sensor hardware is available.

## Dependencies

Phase 01

## Inputs

Running Docker stack or local backend/frontend; synthetic session.

## Tasks

- [x] Generate and save reproducible multimodal synthetic sessions
- [x] Replay compact telemetry and raw batches to FastAPI
- [ ] Verify WebSocket delivery, dashboard values and SYNTHETIC DATA marker

## Files Expected To Change

AI/synthetic/...; AI/simulator/mock_device.py; backend/...; frontend/...; docs/SYNTHETIC_DATA_SPEC.md

## Implementation Notes

Use one shared contract, mark origin SYNTHETIC, send compact telemetry and optional raw batches, and test disconnect/reconnect separately from acquisition.

## Tests

Run automated contract/reproducibility/WebSocket tests; start stack; replay each scenario; observe dashboard marker and fields.

## Acceptance Criteria

- [x] Required synthetic scenarios satisfy the raw contract and reproducibility tests
- [x] Mock telemetry is accepted and broadcast through WebSocket
- [ ] React dashboard receives fields and visibly identifies synthetic origin

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 02; no automatic work on the next phase.

## Known Risks

A headless environment may verify builds but not visual runtime; transport pause may be mistaken for acquisition pause.

## Debug / Rollback Strategy

Check backend logs, browser console, WebSocket frames and saved session timestamps.

## Results

Generator, raw-batch replay, compact telemetry, network-pause recovery and live WebSocket broadcast were verified. Frontend compiled, served HTTP 200 and contains the synthetic marker/telemetry components. Visual browser verification could not be executed because no controllable browser was available, so this phase remains IN_PROGRESS.

## Completion Evidence

- AI/synthetic suite: 15 tests passed, including scenarios, contract, shared preprocessing, reproducibility, profiles, counts/ranges and transitions.
- Docker mock replay sent ATTENTION telemetry and raw batches accepted by the backend.
- Live WebSocket test received device SIM-E2E with origin SYNTHETIC after HTTP 202 ingestion.
- Raw JSONL exists in the backend storage volume.
- Disconnect/reconnect scenario resumed ordered timestamps after a simulated two-second transport pause.
- Frontend production build and container start passed; http://localhost:5173 returned 200.
- Visual field/marker inspection: NOT_VERIFIED (no browser surface available).

## Next Phase

Phase 03 — MAX30102

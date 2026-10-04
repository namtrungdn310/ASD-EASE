# Phase 16 — Edge Inference

## Status

NOT_STARTED

## Owner

SHARED

## Objective

Run the exported model on ESP32 without laptop decisions.

## Why This Phase Exists

Implements the locked Edge-first architecture.

## Dependencies

Phase 15, Phase 00

## Inputs

Verified board limits, export and C++ features.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/src/inference/...

## Implementation Notes

Use bounded memory; quality gate; no PSRAM assumption until verified.

## Tests

Host/firmware build, on-board fixed vectors, memory/latency measurements.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 16; no automatic work on the next phase.

## Known Risks

RAM/flash limits, numeric drift or watchdog resets.

## Debug / Rollback Strategy

Disable model path and inspect fixed-vector stages.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 17 — Parity Test


# Phase 03 — MAX30102

## Status

IN_PROGRESS

## Owner

AUTOMATION

## Objective

Acquire verified MAX30102 red/IR samples on the actual board.

## Why This Phase Exists

Provides the PPG input needed by later integration and algorithms.

## Dependencies

Phase 00, Phase 02

## Inputs

Verified I2C pins, board and MAX30102 wiring.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

ai/edge_firmware/src/sensors/MAX30102Sensor.cpp

## Implementation Notes

The driver implementation is present in PR #7 (`332f249`): SparkFun FIFO reads, contact detection, HR estimation/median/EMA and an optical SpO2 estimate. Raw red/IR capture, sensor-loss behavior, effective rate after averaging and measured accuracy still require physical verification. Source comments/status flags are not measurement evidence.

## Tests

Build/flash; I2C scan; capture ordered samples; test disconnect/contact conditions.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 03; no automatic work on the next phase.

## Known Risks

I2C address, voltage, contact and timing issues.

## Debug / Rollback Strategy

Return to minimal I2C scan and validate power/pull-ups.

## Results

Implementation reviewed from PR #7; physical tests listed above have no recorded acceptance evidence. Host compilation passed, which does not complete this phase.

## Completion Evidence

No physical acceptance log available. Preserve board/commit/config, ordered samples, contact/disconnect tests and timing results before marking DONE.

## Next Phase

Phase 04 — MPU6050


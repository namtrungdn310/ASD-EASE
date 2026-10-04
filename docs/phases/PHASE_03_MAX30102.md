# Phase 03 — MAX30102

## Status

NOT_STARTED

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

AI/edge_firmware/src/sensors/MAX30102Sensor.cpp

## Implementation Notes

Implement real driver only after hardware verification; log raw counts and failures.

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

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 04 — MPU6050


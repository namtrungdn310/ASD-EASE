# Phase 04 — MPU6050

## Status

NOT_STARTED

## Owner

AUTOMATION

## Objective

Acquire calibrated-enough raw accelerometer and gyroscope streams.

## Why This Phase Exists

Movement context is required to interpret artifacts and false alerts.

## Dependencies

Phase 00, Phase 03

## Inputs

Verified I2C bus and MPU6050 hardware.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/src/sensors/MPU6050Sensor.cpp

## Implementation Notes

Configure ranges/rates explicitly and retain raw engineering units.

## Tests

Build/flash; inspect stationary gravity; move/rotate axes; check timing.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 04; no automatic work on the next phase.

## Known Risks

Axis orientation, range saturation or shared-bus faults.

## Debug / Rollback Strategy

Test sensor alone; verify address/range and wiring.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 05 — GSR


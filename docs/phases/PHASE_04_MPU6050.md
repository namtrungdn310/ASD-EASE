# Phase 04 — MPU6050

## Status

IN_PROGRESS

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

ai/edge_firmware/src/sensors/MPU6050Sensor.cpp

## Implementation Notes

Configure ranges/rates explicitly and retain raw engineering units.

PR #7 (`332f249`) implements register reads on `Wire1`, address probing, conversion to engineering units, EMA and reconnect logic. Raw acceleration is currently exposed in m/s² and raw gyroscope values include degrees/s; raw API v1.0 expects g and degrees/s. Driver presence is not proof of offset calibration or correct axis orientation.

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

Implementation reviewed from PR #7; stationary/axis/range/timing and physical calibration checks have not been recorded in this phase. Host compilation passed.

## Completion Evidence

No physical acceptance log available. Supply ordered samples, orientation/range settings, measured timing and disconnect behavior before marking DONE.

## Next Phase

Phase 05 — GSR


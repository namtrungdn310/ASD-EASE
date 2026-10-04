# Phase 05 — GSR

## Status

NOT_STARTED

## Owner

AUTOMATION

## Objective

Acquire raw GSR module ADC counts safely.

## Why This Phase Exists

Adds electrodermal input while preserving calibration limits.

## Dependencies

Phase 00

## Inputs

Verified ADC1-capable pin, module voltage and wiring.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/src/sensors/GSRSensor.cpp

## Implementation Notes

Measure raw ADC only; document attenuation/range and never invent conductance units.

## Tests

Build/flash; open/short/reference checks; range/noise capture.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 05; no automatic work on the next phase.

## Known Risks

Unsafe voltage, ADC nonlinearity, Wi-Fi interaction or contact instability.

## Debug / Rollback Strategy

Disconnect module; validate voltage and ADC pin with references.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 06 — Sensor Integration


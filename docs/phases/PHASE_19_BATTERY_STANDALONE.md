# Phase 19 — Battery Standalone

## Status

NOT_STARTED

## Owner

AUTOMATION

## Objective

Operate ESP32 from verified wearable power without laptop USB.

## Why This Phase Exists

Competition mode requires standalone power.

## Dependencies

Phase 18, Phase 00

## Inputs

Safe verified battery/regulator/charger and integrated firmware.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/...; docs/HARDWARE_PROFILE.md

## Implementation Notes

Measure power/runtime and reset behavior; never assume charging support.

## Tests

USB-disconnected boot, runtime and brownout tests with actual measurements.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 19; no automatic work on the next phase.

## Known Risks

Battery safety, brownout, overheating or insufficient runtime.

## Debug / Rollback Strategy

Disconnect battery safely; bench-supply and inspect reset logs.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 20 — Competition Wireless


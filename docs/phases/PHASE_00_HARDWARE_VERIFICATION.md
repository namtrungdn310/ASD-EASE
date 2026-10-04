# Phase 00 — Hardware Verification

## Status

NOT_STARTED

## Owner

AUTOMATION

## Objective

Inspect the purchased ESP32-S3 Super Mini and record chip, memory, pin, USB and power facts.

## Why This Phase Exists

Physical evidence prevents unsafe board assumptions.

## Dependencies

None

## Inputs

Physical board, cable, multimeter, PlatformIO host tools.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/include/pins.h; docs/HARDWARE_PROFILE.md

## Implementation Notes

Run HardwareProfiler on the physical board; verify pins electrically; record command output.

## Tests

The board or wiring may differ from seller documentation.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 00; no automatic work on the next phase.

## Known Risks

Return pins to unverified values; inspect board markings, boot logs and wiring.

## Debug / Rollback Strategy

Phase 01 — Project Scaffold

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

undefined


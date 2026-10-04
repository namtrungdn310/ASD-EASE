# Phase 06 — Sensor Integration

## Status

NOT_STARTED

## Owner

AUTOMATION

## Objective

Run all three sensors with synchronized, bounded acquisition.

## Why This Phase Exists

Later logging/features require aligned streams.

## Dependencies

Phases 03–05

## Inputs

Verified sensor drivers and timing targets.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/src/sensors/...; AI/edge_firmware/src/processing/...

## Implementation Notes

Use non-blocking schedules and timestamps; quantify missed samples.

## Tests

Combined build/flash; rate/count/timestamp tests; bus and ADC stress run.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 06; no automatic work on the next phase.

## Known Risks

I2C contention, blocking reads, heap or timing overruns.

## Debug / Rollback Strategy

Disable one sensor at a time; inspect timing counters.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 07 — Wi-Fi Backend


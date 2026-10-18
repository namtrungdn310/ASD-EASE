# Phase 06 — Sensor Integration

## Status

IN_PROGRESS

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

ai/edge_firmware/src/sensors/...; ai/edge_firmware/src/processing/...

## Implementation Notes

Use non-blocking schedules and timestamps; quantify missed samples.

PR #7 (`332f249`) adds the combined sensor loop, two I2C buses, ADC sampling and one-second Serial reports. Configured loop/read frequencies do not establish measured synchronization or loss-free sampling. Firmware networking/raw batch buffering are subsequent IT work and require their own timing measurements.

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

Combined-loop implementation reviewed from PR #7; host compilation passed. Actual rates, alignment, missing-sample counts and combined hardware stress results are not recorded.

## Completion Evidence

No physical acceptance log available. Supply board/config/commit, per-stream counts/timestamps and stress/disconnect results before marking DONE.

## Next Phase

Phase 07 — Wi-Fi Backend


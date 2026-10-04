# Phase 21 — Network Resilience

## Status

NOT_STARTED

## Owner

SHARED

## Objective

Prove sensing/inference continue through Wi-Fi loss and telemetry resumes.

## Why This Phase Exists

Network must not be an AI dependency.

## Dependencies

Phase 20

## Inputs

Working Edge pipeline and competition LAN.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/src/communication/...

## Implementation Notes

Bound queues/retries and isolate transport timing.

## Tests

Disconnect/reconnect Wi-Fi while observing local sensing/state counters and heap.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 21; no automatic work on the next phase.

## Known Risks

Blocking calls, unbounded queue or reconnect storm.

## Debug / Rollback Strategy

Disable sending, inspect heap/timing and cap retry state.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 22 — Demo Scenarios


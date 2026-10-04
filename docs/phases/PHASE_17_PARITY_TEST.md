# Phase 17 — Parity Test

## Status

NOT_STARTED

## Owner

SHARED

## Objective

Prove Python/C++ feature and prediction parity within defined tolerances.

## Why This Phase Exists

Edge results must match research implementation.

## Dependencies

Phase 16

## Inputs

Golden raw/features and both implementations.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/tests/...; AI/edge_firmware/test/...

## Implementation Notes

Version golden vectors and tolerances; compare intermediate values.

## Tests

Automated golden-vector tests on Python and C++/device.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 17; no automatic work on the next phase.

## Known Risks

Floating-point, window or ordering differences.

## Debug / Rollback Strategy

Bisect pipeline by intermediate vector.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 18 — Temporal Logic


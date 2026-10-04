# Phase 18 — Temporal Logic

## Status

NOT_STARTED

## Owner

SHARED

## Objective

Add temporal state logic for stable NORMAL/ATTENTION/UNCERTAIN transitions.

## Why This Phase Exists

Instant predictions can be noisy and unsuitable for alerts.

## Dependencies

Phase 17

## Inputs

Parity-verified scores and quality flags.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/edge_firmware/src/state/...

## Implementation Notes

Use documented hysteresis/dwell logic; bad quality can override to UNCERTAIN.

## Tests

Sequence tests for transitions, recovery, calibration and missing data.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 18; no automatic work on the next phase.

## Known Risks

Sticky states, excess delay or hard-coded unvalidated thresholds.

## Debug / Rollback Strategy

Replay golden sequences and expose state reasons.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 19 — Battery Standalone


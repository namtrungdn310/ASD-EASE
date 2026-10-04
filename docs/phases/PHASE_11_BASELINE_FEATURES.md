# Phase 11 — Baseline Features

## Status

NOT_STARTED

## Owner

IT

## Objective

Implement personal baselines, rolling windows and shared feature definitions.

## Why This Phase Exists

Avoids one threshold for all participants and enables parity.

## Dependencies

Phase 10

## Inputs

Quality-gated processed streams.

## Tasks

- [ ] Complete the documented implementation without expanding phase scope
- [ ] Run every listed test and preserve evidence
- [ ] Update this phase, PROGRESS, CHANGELOG and decisions when applicable

## Files Expected To Change

AI/src/baseline/...; AI/src/feature_extraction/...

## Implementation Notes

Fit baselines without test leakage; share mathematical definitions with future C++.

## Tests

Window boundary, baseline isolation, missingness and synthetic/real interface tests.

## Acceptance Criteria

- [ ] Objective is demonstrated with non-fabricated evidence
- [ ] All mandatory tests pass
- [ ] Progress and risks are updated before advancing

## Expected Output

A reviewable implementation, test evidence and updated project tracking for Phase 11; no automatic work on the next phase.

## Known Risks

Leakage, unstable baselines or inconsistent window timing.

## Debug / Rollback Strategy

Use golden small arrays and inspect each intermediate.

## Results

Not executed yet.

## Completion Evidence

Not available.

## Next Phase

Phase 12 — Rule Baselines

